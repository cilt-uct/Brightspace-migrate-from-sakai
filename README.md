
# Brightspace : Migrate from Sakai
This repo exports a site from Sakai (https://www.sakailms.org/), runs a set of workflow steps to improve the import outcome, constructs a zip file, uploads to Brightspace (https://www.d2l.com/brightspace/), and after import runs a workflow to enroll users and do some clean-up.

The entire process is tied to the **Migrate to Brightspace [LTI] (tsugi-migrate-to-brightspace)** tool defined here: https://github.com/cilt-uct/tsugi-migrate-to-brightspace

The LTI tool contains the database (see [Database Schema](#database-schema)) that is used to store the state of the conversion process.

## Workflow
The workflows are divided into 3 parts (matching with the task):

 1. `workflow.yaml` - after archiving of Sakai site this is run.
 2. `upload.yaml` - uploading steps, this manages the retry, upload, delays, and file moves related to Brightspace import process that reads a FTP folder.
 3. `update.yaml` - after importing the site you can run some additional steps for clean-up and enrollment.

The workflow steps are defined in the `work` folder with the corresponding file name.

## Configuration

### Directories
The file `base.sh` define the important folders used in the migration scripts.

-  `ARCHIVE_FOLDER` this folder is *exactly* the same as `archive.storage.path` (see [Sakai Configuration Settings](#sakai-configuration-settings)).

-  `OUTPUT_FOLDER` the folder in which the completed zip file (after running the workflow on the archived site) is created and used to upload to Brightspace.

-  `CONVERSION_REPORT_FOLDER` the folder to store the generated conversion report HTML files so that they can be linked to in Sakai and shown in the migration LTI (see *Apache Setup*)

-  `AUTH_PROPERTIES` refers to the file that contains the authentication and URL information, described in more detail below.

### Setting Authentication and URL's
Create a `auth.properties` file from the sample (`auth.properties.sample`):
```
cp auth.properties.sample auth.properties
```
The file contains the URL's and authentication details to connect to the various databases and servers that are used in the migration scripts.

The key prefixes match up with the definition in the `auth` section defined in `config/config.php`.

### Config File (`config/config.php`)

Change the appropriate values in the `config/config.php` to match up with your configuration, important to note are the following items:

```
APP = {
	'sakai_url' : '[Your Sakai URL]',
	'brightspace_url' : '[Your Brightspace URL]',
	'admin_emails' : ['admin@your.url.com'],
	'helpdesk-email' : ('Help Desk','helpdesk@your.url.com'),
	...
	'report': {
		'url' : 'https://[Sakai URL]/amathuba/conversion/',
		...
	}
}
```

### Apache Setup
In your site configuration file:
```
<Directory /data/sakai/otherdata/conversion-reports/>
Options None
AllowOverride None
Require all granted
DirectoryIndex index.html
</Directory>

Alias /amathuba/conversion/ /data/sakai/otherdata/conversion-reports/
```

## Database Schema
See https://github.com/cilt-uct/tsugi-migrate-to-brightspace/blob/main/database.php for the schema for the tables `migration_site` and `migration_site_property`.

## LTI Tool Configuration
See https://github.com/cilt-uct/tsugi-migrate-to-brightspace/blob/main/tool-config_dist.php for configuration of the LTI migration tool, including:
* Maximum allowed Resources size for migration
* URLs to the Brightspace and Sakai instances
* Set of Faculties and Departments to match the Brightspace organisational structure for creating new sites

## Sakai Configuration Settings
Set these properties in `sakai.properties`, `local.properties` or `security.properties` to allow webservice access to the site archive operation:

```
archive.storage.path=/data/sakai/otherdata/archive-site/
webservices.allowlogin = true
webservices.allow = ^192\\.168\\.[0-9.]+$
webservices.log-allowed=true
webservices.log-denied=true
```

Define a regular expression for `webservices.allow` that includes the IP for the server on which these scripts are running.

The ARCHIVE_FOLDER path specified in `base.sh` should provide access to the `archive.storage.path` location. Typically this means that both the Sakai application server and the migration server will mount the same shared network filesystem.

## Sakai Code Dependencies
For reference, see the UCT 21.x Sakai branch https://github.com/cilt-uct/sakai/tree/21.x

Sakai 21.x builds may need to backport these changes:

### SAK-47123 Add SakaiScript method for archiving a site
https://sakaiproject.atlassian.net/browse/SAK-47123
https://github.com/sakaiproject/sakai/commit/b75cb193377d878b43e0a82ca0636de9c9b81c6d

### SAK-47702 Add Sakai namespace prefix to site archive XML files
https://sakaiproject.atlassian.net/browse/SAK-47702
https://github.com/sakaiproject/sakai/commit/4d45774dc2cb56035c2bf9f0e819d9e30a8c4aed
https://github.com/sakaiproject/sakai/commit/5e71970b2f9daeb372817a394e84d367cc8287f6

### SAK-48751 Add DAV namespace to Sakai archive xml files
https://sakaiproject.atlassian.net/browse/SAK-48751
https://github.com/sakaiproject/sakai/pull/11438
https://github.com/sakaiproject/sakai/pull/11438/commits/be93e2bb8e04fac6542b56751a12921dd3d0003b

### SAK-48756 Lessons archiving fix
https://sakaiproject.atlassian.net/browse/SAK-48756
https://github.com/sakaiproject/sakai/pull/11441
https://github.com/sakaiproject/sakai/pull/11441/commits/18de2e623b2ad7f4a68cf90c3381ada52a10aaf1

### SAK-47948 Archive support for GradebookNG
https://sakaiproject.atlassian.net/browse/SAK-47948
https://github.com/sakaiproject/sakai/pull/11506

## SAK-47901 Use ISO8601 for archive date formats 
https://sakaiproject.atlassian.net/browse/SAK-47901
https://github.com/sakaiproject/sakai/pull/11443

## SAK-49164 Samigo escape label filename attribute for EMI QTI export
https://sakaiproject.atlassian.net/browse/SAK-49164
https://github.com/sakaiproject/sakai/pull/11816

## SAK-49813 Use XML 1.1 serialization 
https://sakaiproject.atlassian.net/browse/SAK-49813
https://github.com/sakaiproject/sakai/pull/12417

## Cron Jobs (How to Run it)
Add these cron jobs on the server running the scripts:
```
# every minute check if there is a new migration to run
* * * * * /usr/bin/flock -n /tmp/check_migrations.lockfile python3 [path to script]/check_migrations.py

# every minutes check for upload to run
* * * * * /usr/bin/flock -n /tmp/check_upload.lockfile python3 [path to script]/check_upload.py

# every minutes check for update to run
* * * * * /usr/bin/flock -n /tmp/check_imported.lockfile python3 [path to script]/check_imported.py

# every hour clean up old log and tmp files
0 * * * * [path to script]/cleanup-old.sh
```

## Development
Create a `users.cfg` file from the sample (`users.cfg.sample`):
```
cp users.cfg.sample users.cfg
```

Helps with committing code on the server for the logged in user.

## Running tests
In order to run the full test suite you can use the `run_test.py` script:
```
python run_test.py
```
In order to run a specific file of tests, use the `run_test.py` script and the `--tf` flag:
```
python run_test.py --tf test_db.py
```
In order to run a specific test case, use the `run_test.py` script and the `--tc` flag:
```
python run_test.py --tc test_query_get_records
```

## Size limits
The D2L Bulk Course Import Service accepts zip packages up to 30GB (30,000,000,000 bytes).

Archive size limits are enforced in 3 places:
* in the LTI migration tool, before the archive operation starts (size of site Resources)
* in the export workflow operation (size of site Resources)
* in the zip upload operation (size of import zip file)
