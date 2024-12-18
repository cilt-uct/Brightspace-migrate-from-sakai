#!/usr/bin/python3

from pathlib import Path
from lib.local_auth import getAuth, get_var

# See base.sh
SCRIPT_FOLDER = get_var('SCRIPT_FOLDER')
ARCHIVE_FOLDER = get_var('ARCHIVE_FOLDER')
OUTPUT_FOLDER = get_var('OUTPUT_FOLDER')
CONVERSION_REPORT_FOLDER = get_var('CONVERSION_REPORT_FOLDER')

# Persistent logging
LOG_PATH = Path(SCRIPT_FOLDER) / 'brightspace_migration.log'
LOG_TEST_PATH = Path(SCRIPT_FOLDER) / 'migration_test.log'
LOG_IN_CONSOLE = True
LOG_IN_FILE = True

middleware = getAuth('BrightspaceMiddleware', ['url'])

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
    'sakai': 'Sakai',
    'sakai_archive' : 'SakaiArchive',
    'sakai_db': 'SakaiDb',
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

  # Temporary logs for workflows and operations
  'log_folder' : Path(SCRIPT_FOLDER) / 'log',

  # test / production
  'environment': 'production',
  'script_folder' : SCRIPT_FOLDER,
  'config_folder' : Path(SCRIPT_FOLDER) / 'config',
  'template' : Path(SCRIPT_FOLDER) / 'templates',

  'archive_folder': ARCHIVE_FOLDER,
  'output': OUTPUT_FOLDER,

  'courseinfo': '/data/sakai/otherdata/import/courseinfo.csv',

  # Only accept True or False
  'debug': False,
  'email_logs' : False,
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

  # Create migration failure issues in this JIRA project.
  # Set the project default assignee setting in JIRA.
  'jira': {
    'enabled': True,
    'key': 'MIG',
    'prefix': 'Migration [ERR]',
    'last' : 20
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
    'restricted-ext': Path(SCRIPT_FOLDER) / 'config' / 'restricted_ext.yaml',
    'max_files' : 5000
  },

  'email': {
    'path' : Path(SCRIPT_FOLDER) / 'templates' / 'emails',
  },

  # D2L Brightspace Valence and Content Service APIs
  # See https://docs.valence.desire2learn.com/about.html#principal-version-table
  # org_ou is Identifier from /d2l/api/lp/1.45/organization/info
  # TODO find out how to get the tenantId via API
  'brightspace_api': {
      'base_url' : 'https://amathuba.uct.ac.za',
      'lp_url' : 'https://amathuba.uct.ac.za/d2l/api/lp/1.45',
      'le_url' : 'https://amathuba.uct.ac.za/d2l/api/le/1.74',
      'tenantId': '6d665046-9dc7-49c8-9521-c482b938d31f',
      'orgId': 6606
  },

  # Opencast
  'opencast': {
      'base_url' : 'https://media.uct.ac.za',
      'content_item_path' : '/lti/player/'
  },

  # Local middleware
  'middleware': {
          'base_url': middleware['url'],
          'api_proxy_url': '/d2l/api/call',
          'create_url': '/d2l/api/course/new',
          'import_url': '/d2l/api/course/import_package',
          'course_info_order_url': '/d2l/api/content/order/course_info',
          'course_outline_order_url': '/d2l/api/content/order/course_outline',
          'add_opencast_url': '/d2l/api/oc/series/',
          'add_topic_from_file': '/d2l/api/content/{}/module/{}',
          'update_html_file': '/d2l/api/content/{}/topics/{}/file',
          'course_info_url': '/d2l/api/course/{}',
          'course_content_src': 78969, # AMA-481 : 9944,
          'retries': 10,
          'retry_delay': 180,
  },

  # Mapping Sakai users to Brightspace users in converted sites
  # Sakai users who have both a matching account type and role will be enrolled
  # in the converted Brightspace site ("reference site")
  'users': {
    # Sakai account types to enroll in Brightspace
    'enroll_account_type': ['staff', 'thirdparty', 'student'],

    # Map of Sakai roles to Brightspace role
    'enroll_role_map': {
            # UCT roles
            'Site owner' : 'Owner',
            'Support staff' : 'Owner',
            # Generic Sakai roles to Brightspace
            # 'Instructor' : 'Instructor'
    },
  },

  # Max workflows to run concurrently
  'workflow': {
        'max_jobs': 30,
  },

  # Max jobs to run concurrently for site archiving
  # Max size of Resources collection
  'export': {
        'max_jobs': 10,
        'limit': 35000000000
  },

  # Max jobs to allow in uploading and import states  before uploading new jobs,
  # import expiry time in minutes after upload (360 = 6 hours, 1440 = 24 hours)
  # limit for zip file size for package uploads in update workflow
  'import': {
      'max_jobs' : 10,
      'expiry' : 2160,
      'limit' : 2147483648,
      'manifest' : {
          'rubrics' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'rubrics-import.xml',
          'content' : Path(SCRIPT_FOLDER) / 'templates' / 'manifests' / 'content-import.xml'
      }
   },

  # D2L Bulk Course Import service
  'ftp': {
     # Max zip file upload size in bytes as per D2L BCI limits
    'limit': 35000000000,
    'show_progress': False,
    'log': True,
    'inbox': '/incoming/BulkCourseImport/Inbox',
    'outbox': '/incoming/BulkCourseImport/Outbox',
    # Expiry time in minutes to complete upload
    'expiry' : 300
  },

  # to differentiate zip files (added to front)
  'zip': {
    'site': 'completed_site_',
    'rubrics' : 'rubrics_',
    'content' : 'content_',
    'qti' : 'qti_'
  },

  # Name of the collection used for T&Q inline images and audio (attachments and cross-site)
  'quizzes': {
        'media_collection' : 'quiz_media'
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

  # Map content item URLs to tool providers
  # This enables updating ACLs in third party systems based on URLs used in LTI quicklinks
  'lti': {
      'content_item_urls': {
          'https://media.uct.ac.za/lti/player/' : 'opencast'
      },
      'match' : {
          'https://media.uct.ac.za/lti' : {
              'url': 'https://media.uct.ac.za/lti/player/', 'valid': ['tool']
          },
          'https://mediadev.uct.ac.za/lti' : {
              'url': 'https://mediadev.uct.ac.za/lti/player/', 'valid': ['tool']
          }
      }
  },

  'path': Path().absolute(),

  # Here for the config unittest
  'loaded' : True,
}
