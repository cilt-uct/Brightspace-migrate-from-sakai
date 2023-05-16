#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source $SCRIPT_FOLDER/base.sh

MYDIR=$SCRIPT_FOLDER/migrate_to_brightspace
touch $MYDIR/workflow.exit
touch $MYDIR/upload.exit
touch $MYDIR/import.exit

