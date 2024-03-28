#!/usr/bin/python3

from re import T
from pathlib import Path
from lib.utils import get_var
from lib.local_auth import getAuth

# See base.sh
SCRIPT_FOLDER = get_var('SCRIPT_FOLDER')
ARCHIVE_FOLDER = get_var('ARCHIVE_FOLDER')
OUTPUT_FOLDER = get_var('OUTPUT_FOLDER')
CONVERSION_REPORT_FOLDER = get_var('CONVERSION_REPORT_FOLDER')

LOG_PATH = Path(SCRIPT_FOLDER) / 'brightspace_migration.log'
LOG_IN_CONSOLE = True
LOG_IN_FILE = True

middleware = getAuth('BrightspaceMiddleware')

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
  },

  # In Brightspace the imported site will get this prefix added to their title,
  # and the Semester set to the org unit id provided here
  'site': {
    'prefix': 'Vula reference site: ',
    'test_prefix': 'Vula test conversion: ',
    'semester' : 6653
  },

  'log_folder' : Path(SCRIPT_FOLDER) / 'log',

  # test / production
  'environment': 'production',

  'tmp' : Path(SCRIPT_FOLDER) / 'tmp',
  'template' : Path(SCRIPT_FOLDER) / 'templates',

  'archive_folder': ARCHIVE_FOLDER,
  'output': OUTPUT_FOLDER,

  'courseinfo': '/data/sakai/otherdata/import/courseinfo.csv',

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
    'upload' : 10,
    'import' : 30
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
    'upload' : False,
  },

  'content': {
    'mime-types': Path(SCRIPT_FOLDER) / 'config' / 'mime_types.yaml',
    'restricted-ext': Path(SCRIPT_FOLDER) / 'config' / 'restricted_ext.yaml'
  },

  'email': {
    'path' : Path(SCRIPT_FOLDER) / 'templates' / 'emails',
  },

  # D2L Brightspace Valence APIs
  'brightspace_api': {
      'base_url' : 'https://amathuba.uct.ac.za/d2l/api',
      'le_url' : 'https://amathuba.uct.ac.za/d2l/api/le/1.74',
      'lp_url' : 'https://amathuba.uct.ac.za/d2l/api/lp/1.45',
      'lp': '1.45',
      'le': '1.74'
  },

  # Local middleware
  'middleware': {
          'base_url': middleware[0],
          'api_proxy_url': '/d2l/api/call',
          'create_url': '/d2l/api/course/new',
          'import_url': '/d2l/api/course/import_package',
          'enroll_user_url': '/d2l/api/course/enroll/user',
          'course_info_order_url': '/d2l/api/content/order/course_info',
          'course_outline_order_url': '/d2l/api/content/order/course_outline',
          'add_opencast_url': '/d2l/api/series/',
          'update_html_file': '/d2l/api/content/{}/topics/{}/file',
          'course_info_url': '/d2l/api/course/{}',
          'course_content_src': 9944,
          'retries': 10,
          'retry_delay': 180,
  },

  'course': {
    # Sakai account types to enroll in Amathuba
    'enroll_user_type': ['staff', 'thirdparty', 'student'],

    # Possible roles : "Designer", "Lecturer", "Support Staff", "Tutor", "Student", "Member", "Guest", "Observer", "Staff", "Owner"
    'enroll_user_role': 'Owner',
  },

  # Max workflows to run concurrently
  'workflow': {
        'max_jobs': 30,
  },

  # Max jobs to run concurrently for site archiving
  # Max size of Resources collection
  'export': {
        'max_jobs': 10,
        'limit': 30000000000
  },

  # Max jobs to allow in uploading and import states  before uploading new jobs,
  # import expiry time in minutes after upload (360 = 6 hours, 1440 = 24 hours)
  # limit for zip file size for package uploads in update workflow
  'import': {
      'max_jobs' : 10,
      'hold_test_conversions' : False,
      'expiry' : 1440,
      'limit' : 2147483648,
      'manifest' : {
          'rubrics' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'rubrics-import.xml',
          'content' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'content-import.xml'
      }
   },

  # D2L Bulk Course Import service
  'ftp': {
     # Max zip file upload size in bytes as per D2L BCI limits
    'limit': 30000000000,
    'show_progress': False,
    'log': True,
    'log_output' : Path(SCRIPT_FOLDER) / 'log',
    'inbox': '/incoming/BulkCourseImport/Inbox',
    'outbox': '/incoming/BulkCourseImport/Outbox'
  },

  # to differentiate zip files (added to front)
  'zip': {
    'site': 'completed_site_',
    'rubrics' : 'rubrics_',
    'content' : 'content_'
  },

  # Name of the collection used for T&Q inline images (attachments and cross-site)
  'quizzes': {
        'image_collection' : 'quiz_images'
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
      # these are resources we want to both link and retain as separate Content topics,
      # because Amathuba will render them as PDFs which may be helpful for students
      'type_to_link': ['application/msword',
                       'application/pdf',
                       'application/vnd.ms-powerpoint',
                       'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                       'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
      'ext_to_link': ['pdf','ppt','xls','pptx','xlsx']
  },

  'qna': {
      'xsl': Path(SCRIPT_FOLDER) / 'templates' / 'qna.xsl',
      'collection': 'qna'
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

  'lti': {
          'content_item_urls': {
              'https://media.uct.ac.za/lti/player/' : 'opencast'
          }
  },

  'path': Path().absolute(),

  # Here for the config unittest
  'loaded' : True,
}
