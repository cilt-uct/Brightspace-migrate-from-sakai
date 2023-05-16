#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_FOLDER/base.sh
source $SCRIPT_FOLDER/args.sh

# echo $SITE_ID

rm -rf $ARCHIVE_FOLDER/$SITE_ID-webdav/ 2>/dev/null
rm $OUTPUT_FOLDER/$SITE_ID-fixed.zip 2>/dev/null
rm $OUTPUT_FOLDER/$SITE_ID-rubrics.zip 2>/dev/null

bash show.sh -s $SITE_ID
