# Part of NHClincal. See LICENSE file for full copyright and licensing details.
import logging

from datetime import datetime as dt
from mock import MagicMock
from faker import Faker
from openerp.tests import common
from openerp.osv.orm import except_orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf

_logger = logging.getLogger(__name__)
fake = Faker()


class TestActivity(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestActivity, cls).setUpClass()
        cr, uid = cls.cr, cls.uid
        cls.test_model_pool = cls.registry('test.activity.data.model')
        cls.activity_pool = cls.registry('nh.activity')
        cls.user_pool = cls.registry('res.users')

    def test_create_creates_an_activity(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})

        self.assertTrue(activity_id, msg="Activity create failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.data_model, 'test.activity.data.model',
                         msg="Activity created with the wrong data model")
        self.assertEqual(activity.summary, 'Test Activity Model',
                         msg="Activity default summary not added")
        self.assertEqual(activity.state, 'new',
                         msg="Activity default state not added")

    def test_create_raises_exception_if_no_data_model_is_passed(self):
        cr, uid = self.cr, self.uid
        with self.assertRaises(except_orm):
            self.activity_pool.create(cr, uid, {})

    def test_create_raises_exception_if_data_model_does_not_exist(self):
        cr, uid = self.cr, self.uid
        with self.assertRaises(except_orm):
            self.activity_pool.create(
                cr, uid,
                {'data_model': 'test.activity.non.existent.data.model'})

    def test_create_uses_data_model_description_if_no_summary_given(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model2'})

        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(
            activity.data_model, 'test.activity.data.model2',
            msg="Activity created with the wrong data model")
        # 'Undefined Activity' is _description of nh_activity_data
        self.assertEqual(
            activity.summary, 'Undefined Activity',
            msg="Activity default summary not added")

    def test_create_creates_activity_using_a_summary(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid,
            {
                'data_model': 'test.activity.data.model2',
                'summary': 'Test Activity Data Model'
            }
        )

        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(
            activity.data_model,
            'test.activity.data.model2',
            msg="Activity created with the wrong data model")
        self.assertEqual(
            activity.summary,
            'Test Activity Data Model', msg="Activity set summary incorrect")

    def test_write_does_not_increment_sequence_if_state_not_changed(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        cr.execute("select coalesce(max(sequence), 0) from nh_activity")
        sequence = cr.fetchone()[0]

        self.assertTrue(self.activity_pool.write(
            cr, uid, activity_id, {'user_id': 1}), msg="Activity Write failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.user_id.id, 1,
                         msg="Activity not written correctly")
        self.assertNotEqual(activity.sequence, sequence+1,
                            msg="Activity sequence updated incorrectly")

    def test_write_increments_sequence_if_state_changed(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        cr.execute("select coalesce(max(sequence), 0) from nh_activity")
        sequence = cr.fetchone()[0]

        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertTrue(self.activity_pool.write(
            cr, uid, activity_id, {'state': 'started'}),
            msg="Activity Write failed")
        self.assertEqual(activity.state, 'started',
                         msg="Activity not written correctly")
        self.assertEqual(activity.sequence, sequence+1,
                         msg="Activity sequence not updated")

    def test_get_recursive_created_ids_returns_id_if_activity_is_not_a_creator(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        created_ids = self.activity_pool.get_recursive_created_ids(
            cr, uid, activity_id)
        self.assertEquals(activity_id, created_ids[0])

    def test_get_recursive_created_ids_returns_created_id_and_own_id(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        activity2_id = self.activity_pool.create(
            cr, uid, {'creator_id': activity_id,
                      'data_model': 'test.activity.data.model'})
        rc_ids = self.activity_pool.get_recursive_created_ids(
            cr, uid, activity_id)
        self.assertEqual(set(rc_ids), {activity_id, activity2_id})

    def test_get_recursive_created_ids_returns_ids_created_by_created_activity(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        activity2_id = self.activity_pool.create(
            cr, uid, {'creator_id': activity_id,
                      'data_model': 'test.activity.data.model'})
        activity3_id = self.activity_pool.create(
            cr, uid, {'creator_id': activity2_id,
                      'data_model': 'test.activity.data.model'})

        rc_ids = self.activity_pool.get_recursive_created_ids(
            cr, uid, activity_id)
        self.assertEqual(
            set(rc_ids), {activity_id, activity2_id, activity3_id})
        rc_ids = self.activity_pool.get_recursive_created_ids(
            cr, uid, activity2_id)
        self.assertEqual(set(rc_ids), {activity2_id, activity3_id})
        rc_ids = self.activity_pool.get_recursive_created_ids(
            cr, uid, activity3_id)
        self.assertEqual(set(rc_ids), {activity3_id})

    def test_update_activity_returns_True(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(
            self.activity_pool.update_activity(cr, uid, activity_id),
            msg="Event call failed")

    def test_update_returns_True_when_passed_list_of_ids(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})

        result = self.activity_pool.update_activity(cr, uid, [activity_id])
        self.assertTrue(result, msg="Event call failed")

    def test_data_model_event_raises_exception_when_passed_non_integer(self):
        cr, uid = self.cr, self.uid

        with self.assertRaises(except_orm):
            self.activity_pool.update_activity(cr, uid, 'activity ID')

    def test_data_model_event_raises_exception_when_passed_integer_less_than_1(self):
        cr, uid = self.cr, self.uid

        with self.assertRaises(except_orm):
            self.activity_pool.update_activity(cr, uid, 0)

    def test_submit_creates_new_instance_of_data_model_if_nonexistent(self):
        # testing nh_activity_data?
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertFalse(
            activity.data_ref,
            msg="Activity Submit pre-State error: "
                "The data model already exists")
        self.assertTrue(
            self.activity_pool.submit(
                cr, uid, activity_id, {'field1': 'test'}),
            msg="Activity Submit failed")

        # TODO: test for _get_data_type_selection
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertTrue(
            activity.data_ref,
            msg="Activity Data Model not created after submit")
        self.assertEqual(
            activity.data_ref._name,
            'test.activity.data.model', msg="Wrong Data Model created")
        self.assertEqual(
            activity.data_ref.field1,
            'test', msg="Data Model data not submitted")

    def test_submit_updates_data_on_an_existent_data_model(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.submit(
            cr, uid, activity_id, {'field1': 'test'}),
            msg="Activity Submit failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.data_ref.field1, 'test',
                         msg="Data Model data not submitted")

    def test_submit_raises_exception_on_non_dict_type(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})
        with self.assertRaises(except_orm):
            self.activity_pool.submit(cr, uid, activity_id, 'test3')

    def test_submit_raises_exception_on_completed_and_cancelled_activities(self):
        cr, uid = self.cr, self.uid

        activity_id = self.activity_pool.create(
            cr, uid, {'data_model': 'test.activity.data.model'})

        self.activity_pool.write(cr, uid, activity_id, {'state': 'completed'})
        with self.assertRaises(except_orm):
            self.activity_pool.submit(cr, uid, activity_id, {'field1': 'test4'})
        self.activity_pool.write(cr, uid, activity_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.submit(cr, uid, activity_id, {'field1': 'test4'})

    def test_schedule(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Schedule an activity
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        test_date = [
            '2015-10-10 12:00:00',
            dt(year=2015, month=10, day=10, hour=13, minute=0, second=0),
            '2015-10-09 12:00',
            '2015-10-07']
        self.assertTrue(self.activity_pool.schedule(cr, uid, activity_id, test_date[0]), msg="Activity Schedule failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.state, 'scheduled', msg="Activity state not updated after schedule")
        self.assertEqual(activity.date_scheduled, test_date[0], msg="Activity date_scheduled not updated after schedule")

        # Scenario 2: Scheduling an activity sending wrong formatted parameter as schedule date
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity_id, 2015)
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity_id, 'Not A Date')

        # Scenario 3: Schedule an activity writing the date beforehand
        activity2_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.activity_pool.write(cr, uid, activity2_id, {'date_scheduled': test_date[0]})
        self.assertTrue(self.activity_pool.schedule(cr, uid, activity2_id), msg="Activity Schedule failed")
        activity = self.activity_pool.browse(cr, uid, activity2_id)
        self.assertEqual(activity.state, 'scheduled', msg="Activity state not updated after schedule")
        self.assertEqual(activity.date_scheduled, test_date[0], msg="Activity date_scheduled not updated after schedule")

        # Scenario 4: Scheduling an activity without date
        activity3_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity3_id)

        # Scenario 5: Scheduling an activity with a datetime date
        self.assertTrue(self.activity_pool.schedule(cr, uid, activity_id, test_date[1]), msg="Activity Schedule failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.date_scheduled, '2015-10-10 13:00:00', msg="Activity date_scheduled not updated after schedule")

        # Scenario 6: Scheduling an activity with different date formats
        self.assertTrue(self.activity_pool.schedule(cr, uid, activity_id, test_date[2]), msg="Activity Schedule failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.date_scheduled, '2015-10-09 12:00:00', msg="Activity date_scheduled not updated after schedule")
        self.assertTrue(self.activity_pool.schedule(cr, uid, activity_id, test_date[3]), msg="Activity Schedule failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.date_scheduled, '2015-10-07 00:00:00', msg="Activity date_scheduled not updated after schedule")

        # Scenario 7: Scheduling activities on not allowed states
        self.activity_pool.schedule(cr, uid, activity3_id, test_date[0])
        self.activity_pool.write(cr, uid, activity_id, {'state': 'started'})
        self.activity_pool.write(cr, uid, activity2_id, {'state': 'completed'})
        self.activity_pool.write(cr, uid, activity3_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity_id)
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity2_id)
        with self.assertRaises(except_orm):
            self.activity_pool.schedule(cr, uid, activity3_id)

    def test_assign(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Assign a new activity
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.assign(cr, uid, activity_id, uid), msg="Assign Activity failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.user_id.id, uid, msg="User id not updated after Assign")

        # Scenario 2: Assign an assigned activity
        user_ids = self.user_pool.search(cr, uid, [['id', '!=', uid]])
        with self.assertRaises(except_orm):
            self.activity_pool.assign(cr, uid, activity_id, user_ids[0])

        # Scenario 3: Assign an activity sending a wrong user_id argument
        self.activity_pool.write(cr, uid, activity_id, {'user_id': False})
        with self.assertRaises(except_orm):
            self.activity_pool.assign(cr, uid, activity_id, 'User ID')

        # Scenario 4: Assign an activity in not allowed states
        self.activity_pool.write(cr, uid, activity_id, {'state': 'completed'})
        with self.assertRaises(except_orm):
            self.activity_pool.assign(cr, uid, activity_id, uid)
        self.activity_pool.write(cr, uid, activity_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.assign(cr, uid, activity_id, uid)

        # Scenario 5: Assign an activity already assigned
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.assign(cr, uid, activity_id, uid), msg="Assign Activity Failed")
        self.activity_pool.assign(cr, uid, activity_id, uid)
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEquals(activity.assign_locked, True)

    def test_unassign(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Unassign a new activity
        activity_id = self.activity_pool.create(cr, uid, {'user_id': uid,
                                                          'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.unassign(cr, uid, activity_id), msg="Activity Unassign failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertFalse(activity.user_id, msg="Activity not unassigned after Unassign")

        # Scenario 2: Unassign an activity not assigned
        with self.assertRaises(except_orm):
            self.activity_pool.unassign(cr, uid, activity_id)

        # Scenario 3: Unassign an activity with a user not assigned to it
        user_ids = self.user_pool.search(cr, uid, [['id', '!=', uid]])
        self.activity_pool.write(cr, uid, activity_id, {'user_id': user_ids[0]})
        with self.assertRaises(except_orm):
            self.activity_pool.unassign(cr, uid, activity_id)

        # Scenario 4: Unassign an activity in not allowed states
        self.activity_pool.write(cr, uid, activity_id, {'state': 'completed', 'user_id': uid})
        with self.assertRaises(except_orm):
            self.activity_pool.unassign(cr, uid, activity_id)
        self.activity_pool.write(cr, uid, activity_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.unassign(cr, uid, activity_id)

        # Scenario 5: Unassign an activity which is locked
        self.activity_pool.write = MagicMock()
        activity_id = self.activity_pool.create(
            cr, uid, {'user_id': uid, 'data_model': 'test.activity.data.model', 'assign_locked': True}
        )
        self.activity_pool.unassign(cr, uid, activity_id)
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertTrue(activity.assign_locked)
        self.assertFalse(self.activity_pool.write.called)
        del self.activity_pool.write

    def test_start(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Start a new activity
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.start(cr, uid, activity_id), msg="Activity Start failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.state, 'started', msg="Activity state not updated after Start")
        self.assertAlmostEqual(activity.date_started, dt.now().strftime(dtf), msg="Activity date started not updated after Start")

        # Scenario 2: Start an activity in not allowed states
        with self.assertRaises(except_orm):
            self.activity_pool.start(cr, uid, activity_id)
        self.activity_pool.write(cr, uid, activity_id, {'state': 'completed'})
        with self.assertRaises(except_orm):
            self.activity_pool.start(cr, uid, activity_id)
        self.activity_pool.write(cr, uid, activity_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.start(cr, uid, activity_id)

    def test_complete(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Complete a new activity
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.complete(cr, uid, activity_id), msg="Activity Complete failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.state, 'completed', msg="Activity state not updated after Complete")
        self.assertAlmostEqual(activity.date_terminated, dt.now().strftime(dtf), msg="Activity date terminated not updated after Complete")
        self.assertEqual(activity.terminate_uid.id, uid, msg="Activity completion user not updated after Complete")

        # Scenario 2: Complete an activity in not allowed states
        with self.assertRaises(except_orm):
            self.activity_pool.complete(cr, uid, activity_id)
        self.activity_pool.write(cr, uid, activity_id, {'state': 'cancelled'})
        with self.assertRaises(except_orm):
            self.activity_pool.complete(cr, uid, activity_id)

    def test_cancel(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Cancel a new activity
        activity_id = self.activity_pool.create(cr, uid, {'data_model': 'test.activity.data.model'})
        self.assertTrue(self.activity_pool.cancel(cr, uid, activity_id), msg="Activity Cancel failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.state, 'cancelled', msg="Activity state not updated after Cancel")
        self.assertAlmostEqual(activity.date_terminated, dt.now().strftime(dtf), msg="Activity date terminated not updated after Cancel")
        self.assertEqual(activity.terminate_uid.id, uid, msg="Activity completion user not updated after Cancel")

        # Scenario 2: Cancel an activity in not allowed states
        with self.assertRaises(except_orm):
            self.activity_pool.cancel(cr, uid, activity_id)
            
    def test_is_action_allowed(self):
        cr, uid = self.cr, self.uid
        
        # Scenario 1: Schedule action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'schedule'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'schedule'))
        self.assertFalse(self.test_model_pool.is_action_allowed('started', 'schedule'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'schedule'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'schedule'))
        
        # Scenario 2: Start action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'start'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'start'))
        self.assertFalse(self.test_model_pool.is_action_allowed('started', 'start'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'start'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'start'))
        
        # Scenario 3: Complete action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'complete'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'complete'))
        self.assertTrue(self.test_model_pool.is_action_allowed('started', 'complete'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'complete'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'complete'))
        
        # Scenario 4: Cancel action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'cancel'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'cancel'))
        self.assertTrue(self.test_model_pool.is_action_allowed('started', 'cancel'))
        self.assertTrue(self.test_model_pool.is_action_allowed('completed', 'cancel'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'cancel'))
        
        # Scenario 5: Submit action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'submit'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'submit'))
        self.assertTrue(self.test_model_pool.is_action_allowed('started', 'submit'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'submit'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'submit'))
        
        # Scenario 6: Assign action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'assign'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'assign'))
        self.assertTrue(self.test_model_pool.is_action_allowed('started', 'assign'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'assign'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'assign'))
        
        # Scenario 7: Unassign action
        self.assertTrue(self.test_model_pool.is_action_allowed('new', 'unassign'))
        self.assertTrue(self.test_model_pool.is_action_allowed('scheduled', 'unassign'))
        self.assertTrue(self.test_model_pool.is_action_allowed('started', 'unassign'))
        self.assertFalse(self.test_model_pool.is_action_allowed('completed', 'unassign'))
        self.assertFalse(self.test_model_pool.is_action_allowed('cancelled', 'unassign'))
        
    def test_check_action(self):
        cr, uid = self.cr, self.uid
        
        # Scenario 1: Schedule action
        self.assertTrue(self.test_model_pool.check_action('new', 'schedule'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'schedule'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('started', 'schedule')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'schedule')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'schedule')
        
        # Scenario 2: Start action
        self.assertTrue(self.test_model_pool.check_action('new', 'start'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'start'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('started', 'start')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'start')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'start')
        
        # Scenario 3: Complete action
        self.assertTrue(self.test_model_pool.check_action('new', 'complete'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'complete'))
        self.assertTrue(self.test_model_pool.check_action('started', 'complete'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'complete')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'complete')
        
        # Scenario 4: Cancel action
        self.assertTrue(self.test_model_pool.check_action('new', 'cancel'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'cancel'))
        self.assertTrue(self.test_model_pool.check_action('started', 'cancel'))
        self.assertTrue(self.test_model_pool.check_action('completed', 'cancel'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'cancel')
        
        # Scenario 5: Submit action
        self.assertTrue(self.test_model_pool.check_action('new', 'submit'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'submit'))
        self.assertTrue(self.test_model_pool.check_action('started', 'submit'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'submit')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'submit')
        
        # Scenario 6: Assign action
        self.assertTrue(self.test_model_pool.check_action('new', 'assign'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'assign'))
        self.assertTrue(self.test_model_pool.check_action('started', 'assign'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'assign')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'assign')
        
        # Scenario 7: Unassign action
        self.assertTrue(self.test_model_pool.check_action('new', 'unassign'))
        self.assertTrue(self.test_model_pool.check_action('scheduled', 'unassign'))
        self.assertTrue(self.test_model_pool.check_action('started', 'unassign'))
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('completed', 'unassign')
        with self.assertRaises(except_orm):
            self.test_model_pool.check_action('cancelled', 'unassign')

    def test_create_activity(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Create an new Activity from Test Data Model
        activity_id = self.test_model_pool.create_activity(cr, uid, {}, {'field1': 'test'})
        self.assertTrue(activity_id, msg="Create Activity from data model failed")
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.data_model, 'test.activity.data.model', msg="Create Activity set wrong data model")
        self.assertEqual(activity.create_uid.id, uid, msg="Create Activity set wrong creator User")
        self.assertEqual(activity.data_ref.field1, 'test', msg="Create Activity recorded wrong data in Data Model")

        # Scenario 2: Create an new Activity from Test Data Model without data
        activity_id = self.test_model_pool.create_activity(cr, uid, {}, {})
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertFalse(activity.data_ref, msg="Create Activity added data model object without having Data")

        # Scenario 3: Create a new Activity with wrong data parameters
        with self.assertRaises(except_orm):
            activity_id = self.test_model_pool.create_activity(cr, uid, 'test', {})
        with self.assertRaises(except_orm):
            activity_id = self.test_model_pool.create_activity(cr, uid, {}, 'test')

    def test_submit_ui(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Submit data through submit_ui
        activity_id = self.test_model_pool.create_activity(cr, uid, {}, {'field1': 'test'})
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.test_model_pool.submit_ui(cr, uid, [activity.data_ref.id], context={'active_id': activity_id})

        # Scenario 2: Try to submit data using submit_ui without context
        self.test_model_pool.submit_ui(cr, uid, [activity.data_ref.id])

    def test_complete_ui(self):
        cr, uid = self.cr, self.uid

        # Scenario 1: Complete activity through complete_ui
        activity_id = self.test_model_pool.create_activity(cr, uid, {}, {'field1': 'test'})
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.test_model_pool.complete_ui(cr, uid, [activity.data_ref.id], context={'active_id': activity_id})
        activity = self.activity_pool.browse(cr, uid, activity_id)
        self.assertEqual(activity.state, 'completed')

        # Scenario 2: Try to complete activity using complete_ui without context
        self.test_model_pool.complete_ui(cr, uid, [activity.data_ref.id])