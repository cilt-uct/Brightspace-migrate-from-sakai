#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

AUTH_PROPERTIES=$SCRIPT_FOLDER'/auth.properties'

SAKAI_DATA_FOLDER='/data/sakai/otherdata/'

ARCHIVE_FOLDER=$SAKAI_DATA_FOLDER'/archive-site/'
OUTPUT_FOLDER=$SAKAI_DATA_FOLDER'/brightspace-import/'
WEBDAV_FOLDER=$SAKAI_DATA_FOLDER'/brightspace-webdav/'
CONVERSION_REPORT_FOLDER=$SAKAI_DATA_FOLDER'/conversion-reports/'