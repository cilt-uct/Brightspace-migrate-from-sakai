#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_FOLDER/base.sh

# Remove tmp and log files older than 3 days
find $SCRIPT_FOLDER/tmp/* -type f -mtime +3 -exec rm -f {} \; > /dev/null 2>&1;
find $SCRIPT_FOLDER/log/* -type f -mtime +3 -exec rm -f {} \; > /dev/null 2>&1;
