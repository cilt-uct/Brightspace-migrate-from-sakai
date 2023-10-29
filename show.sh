#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_FOLDER/base.sh
source $SCRIPT_FOLDER/args.sh

echo
echo "-- Archive Folder ---------------"
du -s $ARCHIVE_FOLDER/$SITE_ID-archive/ 2>/dev/null
du -sh $ARCHIVE_FOLDER/$SITE_ID-archive/ 2>/dev/null
echo
echo "-- Original Zip -----------------"
ls -lra $ARCHIVE_FOLDER/$SITE_ID-2*.zip 2>/dev/null | head -1
ls -lrah $ARCHIVE_FOLDER/$SITE_ID-2*.zip 2>/dev/null | head -1
echo
echo "-- Fixed Zip --------------------"
ZIP=$(echo "$OUTPUT_FOLDER/*"$SITE_ID"_fixed*.zip")
ls -la $ZIP 2>/dev/null
ls -lah $ZIP 2>/dev/null
echo
echo "-- Rubrics Zip --------------------"
ZIP=$(echo "$OUTPUT_FOLDER/*"$SITE_ID"_rubrics*.zip")
ls -lah $ZIP 2>/dev/null
echo
