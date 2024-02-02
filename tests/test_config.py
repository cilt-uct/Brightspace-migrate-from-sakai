import unittest
import yaml
import json

from pathlib import Path
from emails.template import JinjaTemplate as T
from jinja2 import Environment, FileSystemLoader, select_autoescape

import lib.utils
import config

from config.config import *

class QueryTestCase(unittest.TestCase):
    def test_config(self):

        # global config
        global APP
        self.assertTrue(APP['loaded'])

        # Workflow files
        WORKFLOW_FILE = f'{SCRIPT_FOLDER}/update.yaml'
        workflow_steps = lib.utils.read_yaml(WORKFLOW_FILE)

        WORKFLOW_FILE = f'{SCRIPT_FOLDER}/upload.yaml'
        workflow_steps = lib.utils.read_yaml(WORKFLOW_FILE)

        WORKFLOW_FILE = f'{SCRIPT_FOLDER}/workflow.yaml'
        workflow_steps = lib.utils.read_yaml(WORKFLOW_FILE)

        # Other YAML
        mime_types = lib.utils.read_yaml(APP['content']['mime-types'])
        self.assertTrue(len(mime_types['FILES']) > 0)

        restricted_ext = lib.utils.read_yaml(APP['content']['restricted-ext'])
        self.assertTrue(len(restricted_ext['RESTRICTED_EXT']) > 0)

        # JSON Configs
        with open(APP['report']['json']) as json_file:
            conf=json.load(json_file)
            self.assertTrue(len(conf['issues']) > 0)
            self.assertTrue(len(conf['tools']) > 0)

        with open(APP['lessons']['styles']) as json_file:
            conf = json.load(json_file)
            self.assertTrue(len(conf['general']['tags.to.search']) > 0)

    # Test the email templates for valid syntax
    def test_template_syntax(self):

        global APP
        env = Environment(
            loader=FileSystemLoader(APP['email']['path']),
            autoescape=select_autoescape(['html', 'xml'])
        )

        p = Path(APP['email']['path'])
        template_files = list(p.glob('*.html'))

        # Parameters used in conditions
        kwargs = {}
        kwargs['target_site_id'] = 0
        kwargs['create_course_offering'] = 1
        kwargs['target_site_created'] = 0

        for template_file in template_files:
            template = env.get_template(template_file.name)
            rendered = template.render(**kwargs)
            self.assertTrue(len(rendered))

if __name__ == '__main__':
    unittest.main(failfast=True)
