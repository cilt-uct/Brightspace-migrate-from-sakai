import unittest
import os

import config.config
import run_update
import run_workflow
import lib.utils
from check_imported import check_imported
from check_migrations import check_migrations
from unittest.mock import patch

from config.config import APP


class RunUpdateEmailTemplateTestCase(unittest.TestCase):
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('lib.db.get_record', return_value={
            'link_id': 'link_id_12345',
            'notification': 'cilt1@uct.ac.za',
            'site_id': 'site_id_12345',
            'active': 'true',
            'state': 'active',
            'expired': 'N',
            'files': '{}',
            'workflow': '{"workflow":"test_workflow"}',
            'title': 'test_title',
            'transfer_site_id': 'transfer_site_id_12345',
            'imported_site_id': 'imported_site_id_12345',
            'url': 'url.com',
            'report_url': 'report.com',
            'started_by_email': 'cilt@uct.ac.za',
            'failure_type': 'failure_type',
            'failure_detail': 'failure_detail',
            'target_site_id': 98765,
            'target_title': 'New site for 2023',
        })
    @patch('work.archive_site.archive_site_retry', return_value=True)
    @patch('lib.utils.read_yaml', return_value={'STEPS': [{'action': 'mail', 'template': 'finished',
                                                           'subject': 'my email subject'}]})
    @patch('run_update.set_site_property')
    @patch('jinja2.environment.Environment.get_template')
    @patch('run_update.close_jira')
    @patch('jinja2.environment.Template.render')
    def test_start_workflow(
            self, mock_render, *_):
        APP = config.config.APP
        dir = 'tmp'
        parent_dir = '..'
        path = os.path.join(parent_dir, dir)
        try:
            os.mkdir(path)
        except FileExistsError as e:
            print(str(e))
        run_update.start_workflow(link_id='link_id_12345', site_id='site_id_12345', APP=APP)
        self.assertTrue(mock_render.called)
        self.assertEqual('test_title', mock_render.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_render.call_args.kwargs['site_id'])
        self.assertEqual('imported_site_id_12345', mock_render.call_args.kwargs['amathuba_id'])
        self.assertEqual('report.com', mock_render.call_args.kwargs['report_url'])

    @patch('jinja2.environment.Template.render')
    @patch('jinja2.environment.Environment.get_template')
    def test_send_template_email_finished(self, _, mock_render):
        kwargs = {
            'subject': 'test',
            'site_id': 'site_id_12345',
            'title': 'title',
            'amathuba_id': 'imported_site_id_12345',
            'report_url': 'report.com',
            'started_by': 'cilt1@uct.ac.za'
        }
        workflow = lib.utils.send_template_email(
            APP, template='finished.html', to='cilt@uct.ac.za', subj='test', **kwargs)
        self.assertIsNotNone(workflow)
        self.assertTrue(mock_render.called)
        self.assertEqual('title', mock_render.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_render.call_args.kwargs['site_id'])
        self.assertEqual('imported_site_id_12345', mock_render.call_args.kwargs['amathuba_id'])
        self.assertEqual('report.com', mock_render.call_args.kwargs['report_url'])

    @patch('jinja2.environment.Template.render')
    @patch('jinja2.environment.Environment.get_template')
    def test_send_template_email_finished_newsite(self, _, mock_render):
        kwargs = {
            'subject': 'test',
            'site_id': 'site_id_12345',
            'title': 'title',
            'amathuba_id': 'imported_site_id_12345',
            'report_url': 'report.com',
            'started_by': 'cilt1@uct.ac.za',
            'target_site_id': 98765,
            'target_title': 'New site for 2023'
        }
        workflow = lib.utils.send_template_email(
            APP, template='finished.html', to='cilt@uct.ac.za', subj='test', **kwargs)
        self.assertIsNotNone(workflow)
        self.assertTrue(mock_render.called)
        self.assertEqual('title', mock_render.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_render.call_args.kwargs['site_id'])
        self.assertEqual('imported_site_id_12345', mock_render.call_args.kwargs['amathuba_id'])

    @patch('lib.utils.send_email')
    @patch('jinja2.environment.Environment.get_template')
    def test_send_template_email_with_started_by(self, _, mock_send_email):
        kwargs = {
            'subject': 'test',
            'site_id': 'site_id_12345',
            'title': 'title',
            'amathuba_id': 'imported_site_id_12345',
            'report_url': 'report.com',
            'started_by': 'cilt@uct.ac.za'
        }
        workflow = lib.utils.send_template_email(
            APP, template='finished.html', to=None, subj='test', **kwargs)
        self.assertIsNotNone(workflow)
        self.assertTrue(mock_send_email.called)
        self.assertEqual('cilt@uct.ac.za', mock_send_email.call_args.args[1][0])

    @patch('lib.utils.send_email')
    @patch('jinja2.environment.Environment.get_template')
    def test_send_template_email_with_to_and_started_by(self, _, mock_send_email):
        kwargs = {
            'subject': 'test',
            'site_id': 'site_id_12345',
            'title': 'title',
            'amathuba_id': 'imported_site_id_12345',
            'report_url': 'report.com',
            'started_by': 'cilt@uct.ac.za'
        }
        workflow = lib.utils.send_template_email(
            APP, template='finished.html', to='cilt1@uct.ac.za', subj='test', **kwargs)
        self.assertIsNotNone(workflow)
        self.assertTrue(mock_send_email.called)
        self.assertEqual('cilt1@uct.ac.za', mock_send_email.call_args.args[1][0])
        self.assertEqual('cilt@uct.ac.za', mock_send_email.call_args.args[1][1])

    @patch('jinja2.environment.Template.render')
    @patch('jinja2.environment.Environment.get_template')
    def test_run_workflow_step(self, _, mock_render):
        step = {
            'action': 'mail',
            'template': 'finished',
            'subject': 'test',
        }

        kwargs = {
            'to': 'cilt@uct.ac.za',
            'title': 'title',
            'import_id': 'imported_site_id_12345',
            'report_url': 'report.com',
            'started_by': 'cilt1@uct.ac.za',
            'target_site_id': 98765,
            'target_title': 'New site for 2023',
        }
        workflow = run_update.run_workflow_step(step=step, site_id='site_id_12345', log_file='', db_config='',  **kwargs)
        self.assertIsNotNone(workflow)
        self.assertTrue(mock_render.called)
        self.assertEqual('title', mock_render.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_render.call_args.kwargs['site_id'])
        self.assertEqual('imported_site_id_12345', mock_render.call_args.kwargs['amathuba_id'])
        self.assertEqual('report.com', mock_render.call_args.kwargs['report_url'])

    # Test an exception in the update workflow
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('lib.db.get_record', return_value={
        'link_id': 'link_id_12345',
        'notification': 'cilt1@uct.ac.za',
        'site_id': 'site_id_12345',
        'active': 'true',
        'expired': 'N',
        'files': '{}',
        'state': 'active',
        'workflow': '{"workflow":"test_workflow"}',
        'title': 'test_title',
        'transfer_site_id': 'transfer_site_id_12345',
        'imported_site_id': 'imported_site_id_12345',
        'url': 'url.com',
        'report_url': 'report.com',
        'started_by_email': 'cilt@uct.ac.za',
        'failure_type': 'failure_type',
        'failure_detail': 'failure_detail',
        'target_site_id': 98765,
        'target_title': 'New site for 2023'
    })
    @patch('run_update.create_jira')
    @patch('run_update.send_template_email')
    def test_run_update_fail_email(self, mock_send_template_email, *_):
        run_update.start_workflow('link_id', 'site_id', APP)
        self.assertTrue(mock_send_template_email.called)
        self.assertEqual('error_import.html', mock_send_template_email.call_args.kwargs['template'])
        self.assertIsNone(mock_send_template_email.call_args.kwargs['to'])
        self.assertEqual('cilt@uct.ac.za', mock_send_template_email.call_args.kwargs['started_by'])
        self.assertEqual('Sakai to Amathuba: Import failed [test_title]', mock_send_template_email.call_args.kwargs['subj'])
        self.assertEqual('test_title', mock_send_template_email.call_args.kwargs['title'])
        self.assertEqual('site_id', mock_send_template_email.call_args.kwargs['site_id'])

    # This tests an unexpected and unhandled failure in the import check code
    # Triggered by leaving out 'expired' from the result set
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('lib.db.get_records', return_value=[{
        'link_id': 'link_id_12345',
        'notification': 'cilt1@uct.ac.za',
        'site_id': 'site_id_12345',
        'active': 'true',
        'state': 'active',
        'files': '{}',
        'workflow': '{"workflow":"test_workflow"}',
        'title': 'test_title',
        'transfer_site_id': 'transfer_site_id_12345',
        'imported_site_id': 12345,
        'url': 'url.com',
        'report_url': 'report.com',
        'started_by_email': 'cilt@uct.ac.za',
        'notification': 'notifyme@gmail.com',
        'failure_type': 'failure_type',
        'failure_detail': 'failure_detail',
    }])
    @patch('check_imported.check_sftp', return_value=('1', '2'))
    @patch('check_imported.create_jira')
    @patch('check_imported.get_import_status_collection')
    @patch('check_imported.send_template_email')
    def test_check_imported_fail_email(self, mock_send_template_email, *_):
        check_imported(APP)
        self.assertTrue(mock_send_template_email.called)
        self.assertEqual('error_import.html', mock_send_template_email.call_args.kwargs['template'])
        self.assertEqual('notifyme@gmail.com', mock_send_template_email.call_args.kwargs['to'])
        self.assertEqual('cilt@uct.ac.za', mock_send_template_email.call_args.kwargs['started_by'])
        self.assertEqual('Sakai to Amathuba: Import workflow error [test_title]', mock_send_template_email.call_args.kwargs['subj'])
        self.assertEqual('test_title', mock_send_template_email.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_send_template_email.call_args.kwargs['site_id'])

    # This tests the import failure case where the D2L import job has Failed status
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('lib.db.get_records', return_value=[{
        'link_id': 'link_id_12345',
        'notification': 'cilt1@uct.ac.za',
        'site_id': 'site_id_12345',
        'active': 'true',
        'expired': 'N',
        'files': '{}',
        'state': 'active',
        'workflow': '{"workflow":"test_workflow"}',
        'title': 'test_title',
        'transfer_site_id': 'transfer_site_id_12345',
        'imported_site_id': 'imported_site_id_12345',
        'url': 'url.com',
        'report_url': 'report.com',
        'started_by_email': 'cilt@uct.ac.za',
        'failure_type': 'failure_type',
        'failure_detail': 'failure_detail',
        'target_site_id': 98765,
        'target_title': 'New site for 2023'
    }])
    @patch('check_migrations.create_jira')
    @patch('check_migrations.send_template_email')
    def test_check_migrations_fail_email(self, mock_send_template_email, *_):
        check_migrations(APP)
        self.assertTrue(mock_send_template_email.called)
        self.assertEqual('error_workflow.html', mock_send_template_email.call_args.kwargs['template'])
        self.assertIsNone(mock_send_template_email.call_args.kwargs['to'])
        self.assertEqual('cilt@uct.ac.za', mock_send_template_email.call_args.kwargs['started_by'])
        self.assertEqual('Failed conversion', mock_send_template_email.call_args.kwargs['subj'])
        self.assertEqual('test_title', mock_send_template_email.call_args.kwargs['title'])
        self.assertEqual('site_id_12345', mock_send_template_email.call_args.kwargs['site_id'])

    # Tests an exception in running the workflow
    @patch('lib.local_auth.getAuth', return_value=['host', 'db', 'user', 'pass'])
    @patch('lib.db.get_record', return_value={
        'link_id': 'link_id_12345',
        'notification': 'cilt1@uct.ac.za',
        'site_id': 'site_id_12345',
        'active': 'true',
        'expired': 'N',
        'files': '{}',
        'state': 'active',
        'workflow': '{"workflow":"test_workflow"}',
        'title': 'test_title',
        'transfer_site_id': 'transfer_site_id_12345',
        'imported_site_id': 'imported_site_id_12345',
        'url': 'url.com',
        'report_url': 'report.com',
        'started_by_email': 'cilt@uct.ac.za',
        'failure_type': 'failure_type',
        'failure_detail': 'failure_detail',
    })
    @patch('run_workflow.create_jira')
    @patch('run_workflow.send_template_email')
    def test_run_workflow_fail_email(self, mock_send_template_email, *_):
        run_workflow.start_workflow('link_id', 'site_id', APP)
        self.assertTrue(mock_send_template_email.called)
        self.assertEqual('error_workflow.html', mock_send_template_email.call_args.kwargs['template'])
        self.assertIsNone(mock_send_template_email.call_args.kwargs['to'])
        self.assertEqual('cilt@uct.ac.za', mock_send_template_email.call_args.kwargs['started_by'])
        self.assertEqual('Sakai to Amathuba: Failed [site_id]', mock_send_template_email.call_args.kwargs['subj'])
        self.assertEqual('site_id', mock_send_template_email.call_args.kwargs['title'])
        self.assertEqual('site_id', mock_send_template_email.call_args.kwargs['site_id'])


if __name__ == '__main__':
    unittest.main(failfast=True)
