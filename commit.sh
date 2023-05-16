#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_FOLDER

pre-commit
ret=$?
if [ $ret -ne 0 ]; then
    echo
    git status
    exit 0
fi

CURRENT_USER=$(logname)
USERS_FILE=users.cfg

# Get the display name of the user
# params:
# $1 -- the section (if any)
# $2 -- the key
getCurrentUser() {

  section="git"
  key=$CURRENT_USER

  value=$(
    if [ -n "$section" ]; then
      sed -n "/^\[$section\]/, /^\[/p" $USERS_FILE
    else
      cat $USERS_FILE
    fi |

    egrep "^ *\b$key\b *=" |

    head -1 | cut -f2 -d'=' |
    sed 's/^[ "'']*//g' |
    sed 's/[ ",'']*$//g' )

  if [ -n "$value" ]; then
    echo $value
    return
  else
    echo 'NA'
    return
  fi
}

branch_name=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)
user="$(getCurrentUser)"

read -p "[$branch_name] Commit: " msg

read -p "Push [Y/n]: " yn
yn=${yn:-'Y'}

if [[ "$user" != "NA" ]]; then
    git commit --author="$user" -m "$msg"
else
    git commit -m "$msg"
fi

case $yn in
    [Yy]* ) bash push.sh;;
esac
