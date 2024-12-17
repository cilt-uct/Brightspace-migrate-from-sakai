
# Brightspace : Migrate from Sakai
This repo exports a site from Sakai (https://www.sakailms.org/), runs a set of workflow steps to improve the import outcome, constructs a zip file, uploads to Brightspace (https://www.d2l.com/brightspace/), and after import runs a workflow to enroll users and do some clean-up.

The entire process is tied to the **Migrate to Brightspace [LTI] (tsugi-migrate-to-brightspace)** tool defined here: https://github.com/cilt-uct/tsugi-migrate-to-brightspace

The LTI tool contains the database (see [Database Schema](#database-schema)) that is used to store the state of the conversion process.

## Brightspace dependencies

### Bulk Course Import

These conversion scripts use the Brightspace [Bulk Course Import service](https://community.d2l.com/brightspace/kb/articles/25615-set-up-bulk-course-import).

### Shared Files

The templates and scripts create HTML content for import which references shared files and HTML page templates in the Brightspace shared files location.
These templates support migration of content from Sakai Lessons to a look and feel which matches Brightspace pages. Please see 
[thirdpartylib](https://github.com/cilt-uct/Brightspace-HTML-Templates/tree/main/thirdpartylib) and 
[HTML-Template-Library](https://github.com/cilt-uct/Brightspace-HTML-Templates/tree/main/HTML-Template-Library)

These should be copied to the /shared/ location in Brightspace Admin Tools / Shared Files.

## Python dependencies

To install the required versions of the python module dependencies used by these scripts, use

```
pip install --upgrade -r requirements.txt
```

To regenerate the requirements list, use

```
pip install pipreqs
pipreqs
```

## Workflow
The workflows defined in the `config` folder are divided into 3 parts (matching with the task):

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
		'url' : 'https://[Sakai URL]/brightspace/conversion/',
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

Alias /brightspace/conversion/ /data/sakai/otherdata/conversion-reports/
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

The migration code depends on a number of fixes and improvements to the Sakai archive code, listed here:

https://docs.google.com/spreadsheets/d/1iGDYmwoFYNu5BAgB-OG-RsyfjL7msScfCtqj8Z-IfaI/edit?usp=sharing

Check the Fix version for each JIRA to see which you need, and merge the commits for each issue into your Sakai 21, 22 or 23 build.

The migration code is tested with UCT 21.x Sakai branch: https://github.com/cilt-uct/sakai/tree/21.x

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

### Running tests
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

### Code quality

To check python lint-style issues, use:

```
ruff check
```

Ruff configuration is in `ruff.toml`

## Size limits
The D2L [Bulk Course Import Service](https://community.d2l.com/brightspace/kb/articles/23502-introducing-bulk-course-import)
accepts zip packages up to 35GB (35,000,000,000 bytes).

Archive size limits are enforced in 3 places:
* in the LTI migration tool, before the archive operation starts (size of site Resources)
* in the export workflow operation (size of site Resources)
* in the zip upload operation (size of import zip file)
