#!/usr/bin/python3

from re import T
from pathlib import Path
from lib.utils import get_var
from lib.local_auth import getAuth

SCRIPT_FOLDER = get_var('SCRIPT_FOLDER')
ARCHIVE_FOLDER = get_var('ARCHIVE_FOLDER')
OUTPUT_FOLDER = get_var('OUTPUT_FOLDER')
WEBDAV_FOLDER = get_var('WEBDAV_FOLDER')
CONVERSION_REPORT_FOLDER = get_var('CONVERSION_REPORT_FOLDER')

LOG_PATH = Path(SCRIPT_FOLDER) / 'brightspace_migration.log'
LOG_IN_CONSOLE = True
LOG_IN_FILE = True

brightspace = getAuth('BrightspaceMiddleware')
APP = {
  'sakai_url' : 'https://vula.uct.ac.za',
  'sakai_name' : 'Vula',
  'brightspace_url' : 'https://amathuba.uct.ac.za',
  'brightspace_name' : 'Amathuba',
  'admin_emails' : ['corne.oosthuizen@uct.ac.za'],
  'helpdesk-email' : ('Amathuba','cilt-helpdesk@uct.ac.za'),

  # Key prefixes for authentication secrets in auth.properties
  'auth' : {
    'db' : 'Tsugi',
    'sakai': 'Vula',
    'sakai_archive' : 'VulaArchive',
    'sakai_db': 'VulaDb',
    'middleware': 'BrightspaceMiddleware',
    'webAuth': 'BrightspaceWeb',
    'webDAV': 'BrightspaceWebdav'
  },

  # In Brightspace the imported site will get this prefix added to their title
  'site': {
    'prefix': 'Vula reference site: ',
    'test_prefix': 'Vula test conversion: '
  },

  'log_folder' : Path(SCRIPT_FOLDER) / 'log',

  # test / production
  'environment': 'production',

  'tmp' : Path(SCRIPT_FOLDER) / 'tmp',
  'template' : Path(SCRIPT_FOLDER) / 'templates',

  'archive_folder': ARCHIVE_FOLDER,
  'output': OUTPUT_FOLDER,
  'webdav_folder': WEBDAV_FOLDER,

  # Only accept True or False
  'debug': False,
  'clean_up': True,

  'archive' : {
    # Custom UCT endpoint; for regular Sakai use '/sakai-ws/soap/sakai'
    'endpoint' : '/sakai-ws/soap/uct'
  },

  # Execution
  'scan_interval' : {
    'workflow' : 5,
    'upload' : 5,
    'import' : 60
  },

  'exit_flag' : {
    'workflow' : Path(SCRIPT_FOLDER) / 'workflow.exit',
    'upload' : Path(SCRIPT_FOLDER) / 'upload.exit',
    'import' : Path(SCRIPT_FOLDER) / 'import.exit',
  },

  'jira': {
    'enabled': True,
    'prefix': 'Migration [ERR]',
    'key': 'MIG',
    'assignee': 'smarquard',
    'last' : 15
  },

  'report': {
    'url' : 'https://vula.uct.ac.za/amathuba/conversion',
    'output' : CONVERSION_REPORT_FOLDER,
    'json' : Path(SCRIPT_FOLDER) / 'config' / 'conversion_issues.json',
    'template': Path(SCRIPT_FOLDER) / 'templates' / 'conversion_report.html',
    'dev_template': Path(SCRIPT_FOLDER) / 'templates' / 'dev_report.html',
  },

  'content': {
    'mime-types': Path(SCRIPT_FOLDER) / 'config' / 'mime_types.yaml',
    'restricted-ext': Path(SCRIPT_FOLDER) / 'config' / 'restricted_ext.yaml'
  },

  'email': {
    'path' : Path(SCRIPT_FOLDER) / 'templates' / 'emails',
  },

  'middleware': {
          'base_url': brightspace[0],
          'retries': 5,
          'retry_delay': 30,
          'search_url': '/d2l/api/course',
          'create_url': '/d2l/api/course/new',
          'import_url': '/d2l/api/courses/import_package',
          'search_user_url': '/d2l/api/user',
          'enroll_user_url': '/d2l/api/course/enroll/user',
          'copy_url': '/d2l/api/course/copy_orientation',
          'course_info_order_url': '/d2l/api/content/order/course_info',
          'course_outline_order_url': '/d2l/api/content/order/course_outline',
          'course_content_src': 9944
  },

  'course': {
    # Sakai account types to enroll in Amathuba
    'enroll_user_type': ['staff', 'thirdparty', 'student'],

    # Possible roles : "Designer", "Lecturer", "Support Staff", "Tutor", "Student", "Member", "Guest", "Observer", "Staff", "Owner"
    'enroll_user_role': 'Owner',
  },

  # Max jobs to run concurrently for site archiving
  # Max size of Resources collection
  'export': {
        'max_jobs': 10,
        'limit': 32212254720
  },

  # Max jobs to allow in uploading and import states  before uploading new jobs,
  # import expiry time in minutes after upload (360 = 6 hours, 1080 = 18 hours)
  # limit for zip file size for package uploads in update workflow
  'import': {
      'max_jobs' : 10,
      'expiry' : 1080,
      'limit' : 2147483648,
      'manifest' : {
          'rubrics' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'rubrics-import.xml',
          'content' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'content-import.xml'
      }
   },

  # D2L Bulk Course Import service
  'ftp': {
     # Max zip file upload size in bytes (30G)
    'limit': 32212254720,
    'show_progress': False,
    'log': True,
    'log_output' : Path(SCRIPT_FOLDER) / 'log',
    # this should need to change
    'outbox': '/incoming/CourseMigration/Outbox',
    'inbox': '/incoming/CourseMigration/Inbox'
  },

  # to differentiate zip files (added to front)
  'zip': {
    'site': 'completed_site_',
    'rubrics' : 'rubrics_',
    'content' : 'content_'
  },

  'lessons': {
      'styles': Path(SCRIPT_FOLDER) / 'config' / 'lesson_styles.json',
      'replace_strings': {
            'help@vula.uct.ac.za': 'cilt-helpdesk.uct.ac.za',
            'The Vula Help Team': 'CILT Help Desk',
            'Vula Help': 'CILT Help Desk'
        },
      'highlight_names': ['Blogs', 'Calendar', 'Chat Room', 'Commons',
                                  'Gradebook', 'Lessons', 'Polls', 'Rubrics',
                                  'Tests & Quizzes', 'Resources', 'Q&A', 'Lecture Videos', 'Discussions'],
      'highlight_domains': ['vula.uct.ac.za'],
      'type_to_link': ['application/msword', 'application/pdf',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
  },

  'qna': {
      'xsl': Path(SCRIPT_FOLDER) / 'templates' / 'qna.xsl'
  },

  'attachment': {
        # Mapping tool paths in /attachment/ to tool XML files
        'paths': {
            'Announcements' : 'announcement.xml',
            'Assignments' : 'assignment.xml',
            'Discussions' : 'messageforum.xml',
            'Forums' : 'messageforum.xml',
            'Course Outline' : 'syllabus.xml',
            'Tests_Quizzes' : 'qti/*'
        },
        # Extensions not guessed by mimetypes
        'content-types': {
            'text/url' : '.URL',
            'audio/vnd.wave' : '.wav'
        }
  },
  'path': Path().absolute(),
  # Here for the config unittest
  'loaded' : True,
}
