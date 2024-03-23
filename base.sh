#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

AUTH_PROPERTIES=$SCRIPT_FOLDER'/auth.properties'

# This must match the sakai.properties setting archive.storage.path
ARCHIVE_FOLDER='/data/sakai/otherdata/archive-site/'

# Location to create import zip packages prior to upload
OUTPUT_FOLDER='/data/sakai/otherdata/brightspace-import/'

# Location for conversion report HTML pages
CONVERSION_REPORT_FOLDER='/data/sakai/otherdata/conversion-reports/'
