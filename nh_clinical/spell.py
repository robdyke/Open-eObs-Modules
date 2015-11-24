# -*- coding: utf-8 -*-

from datetime import datetime as dt
import logging

from openerp.osv import orm, fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class nh_clinical_spell(orm.Model):
    """
    A spell represents the time between a patient admission in the hospital and the patient discharge. It will be open
    as long as the patient remains in the hospital and will be connected to every activity related to that patient
    during this period of time.
    """
    _name = 'nh.clinical.spell'
    _inherit = ['nh.activity.data']
    _description = "Spell / Visit"
    
    _rec_name = 'code'
    
    def _get_transferred_user_ids(self, cr, uid, ids, field, arg, context=None):   
        res = {spell_id: False for spell_id in ids} 
        sql = """
            with 
                recursive route(level, path, parent_id, id) as (
                        select 0, id::text, parent_id, id 
                        from nh_clinical_location 
                        where parent_id is null
                    union
                        select level + 1, path||','||location.id, location.parent_id, location.id 
                        from nh_clinical_location location 
                        join route on location.parent_id = route.id
                ),
                parent_location as (
                    select 
                        id as location_id, 
                        ('{'||path||'}')::int[] as ids 
                    from route
                    order by path
                ),
                spell_transferred_locations as(
                    select 
                        spell.id as spell_id,
                        spell_activity.id as activity_id,
                        array_agg(move.from_location_id) as location_ids
                    from nh_clinical_patient_move move
                    inner join nh_activity move_activity on move.activity_id = move_activity.id
                        and move.from_location_id is not null 
                        and move_activity.state = 'completed'
                    inner join nh_activity spell_activity on move_activity.parent_id = spell_activity.id
                    inner join nh_activity transfer_activity on move_activity.creator_id = transfer_activity.id
                        and transfer_activity.data_model = 'nh.clinical.patient.transfer'
                    inner join nh_clinical_spell spell on spell.activity_id = spell_activity.id
                    where now() at time zone 'UTC' - move_activity.date_terminated < interval '1d'
                        and spell_activity.state = 'started'
                    group by spell_id, spell_activity.id
                ),
                user_locations as (
                    select
                        user_id,
                        array_agg(location_id) as location_ids
                    from user_location_rel
                    group by user_id
                )
            select
                stl.activity_id,
                stl.spell_id,
                array_agg(ul.user_id) as user_ids
            from spell_transferred_locations stl
            inner join parent_location on stl.location_ids && parent_location.ids
            left join user_locations ul on ul.location_ids && parent_location.ids
            where stl.spell_id in (%s)
            group by activity_id, stl.spell_id
        """ % ",".join(map(str, ids))
        cr.execute(sql)
        rows = cr.dictfetchall()
        [res.update({row['spell_id']: list(set(row['user_ids']))}) for row in rows]
        return res
    
    def _transferred_user_ids_search(self, cr, uid, obj, name, args, domain=None, context=None):
        arg1, op, arg2 = args[0]
        arg2 = arg2 if isinstance(arg2, (list, tuple)) else [arg2]
        all_ids = self.search(cr, uid, [])
        spell_user_map = self._get_transferred_user_ids(cr, uid, all_ids, 'transferred_user_ids', None)
        spell_ids = [k for k, v in spell_user_map.items() if set(v or []) & set(arg2 or [])]
        
        return [('id', 'in', spell_ids)]   
     
    _columns = {
        'patient_id': fields.many2one('nh.clinical.patient', 'Patient', required=True, ondelete='cascade'),
        'location_id': fields.many2one('nh.clinical.location', 'Placement Location'),
        'pos_id': fields.many2one('nh.clinical.pos', 'Placement Location', required=True),
        'code': fields.char("Code", size=256),
        'start_date': fields.datetime("ADT Start Date"),
        'move_date': fields.datetime("Last Movement Date"),
        'ref_doctor_ids': fields.many2many('nh.clinical.doctor', 'ref_doctor_spell_rel', 'spell_id', 'doctor_id', "Referring Doctors"),
        'con_doctor_ids': fields.many2many('nh.clinical.doctor', 'con_doctor_spell_rel', 'spell_id', 'doctor_id', "Consulting Doctors"),
        'transferred_user_ids': fields.function(_get_transferred_user_ids, fnct_search=_transferred_user_ids_search, type='many2many', relation='res.users', string="Recently Transfered Access"),      
    }
    _defaults = {
        'code': lambda s, cr, uid, c: s.pool['ir.sequence'].next_by_code(cr, uid, 'nh.clinical.spell', context=c),
    }

    def create(self, cr, uid, vals, context=None):
        current_spell_id = self.search(cr, uid, [['patient_id', '=', vals['patient_id']],
                                                 ['state', '=', 'started']], context=context)
        if current_spell_id:
            res = current_spell_id[0]
            _logger.warn("Started spell already exists! Current spell ID=%s returned." % current_spell_id[0])
        else:        
            res = super(nh_clinical_spell, self).create(cr, uid, vals, context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if 'location_id' in vals:
            vals['move_date'] = dt.now().strftime(DTF)
        return super(nh_clinical_spell, self).write(cr, uid, ids, vals, context=context)

    def get_activity_user_ids(self, cr, uid, activity_id, context=None):
        cr.execute("select location_id from nh_activity where id = %s" % activity_id)
        if not cr.fetchone()[0]:
            return []
        sql = """
            with 
                recursive route(level, path, parent_id, id) as (
                        select 0, id::text, parent_id, id 
                        from nh_clinical_location 
                        where parent_id is null
                    union
                        select level + 1, path||','||location.id, location.parent_id, location.id 
                        from nh_clinical_location location 
                        join route on location.parent_id = route.id
                ),
                parent_location as (
                    select 
                        id as location_id, 
                        ('{'||path||'}')::int[] as ids 
                    from route
                    order by path
                )
            select
                activity.id as activity_id,
                array_agg(ulr.user_id) as user_ids
            from user_location_rel ulr
            inner join res_groups_users_rel gur on ulr.user_id = gur.uid
            inner join ir_model_access access on access.group_id = gur.gid and access.perm_responsibility = true
            inner join ir_model model on model.id = access.model_id and model.model = 'nh.clinical.spell'
            inner join parent_location on parent_location.ids  && array[ulr.location_id]
            inner join nh_activity activity on model.model = activity.data_model 
                and activity.location_id = parent_location.location_id
                and activity.id = %s
            group by activity.id
                """ % activity_id
        cr.execute(sql)
        res = cr.dictfetchone()
        user_ids = list(res and set(res['user_ids']) or [])
        return user_ids

    def get_by_patient_id(self, cr, uid, patient_id, exception=False, context=None):
        """
        Checks if there is a started spell for the provided Patient
        :param exception: string with values 'True' or 'False'.
        :return: if no exception parameter is provided: spell id if exists. False if not.
                if exception = 'True': Integrity Error exception is raised if spell exists. False if not.
                if exception = 'False': spell id if exists. No Started Spell exception is raised if not.
        """
        domain = [['patient_id', '=', patient_id], ['activity_id.state', '=', 'started']]
        spell_id = self.search(cr, uid, domain, context=context)
        if exception:
            if spell_id and eval(exception):
                raise osv.except_osv('Integrity Error!', 'Patient with id %s already has a started spell!'
                                     % patient_id)
            elif not spell_id and not eval(exception):
                raise osv.except_osv('Spell Not Found!', 'There is no started spell for patient with id %s' %
                                     patient_id)
        return spell_id[0] if spell_id else False