#! /bin/bash

SCRIPT_FOLDER=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_FOLDER

branch_name=$(git rev-parse --symbolic-full-name --abbrev-ref HEAD)

read -p "Branch [$branch_name]: " branch
branch=${branch:-$branch_name}

read -p "Github Username (not email): " username

git push https://$username@github.com/cilt-uct/Brightspace-migrate-from-sakai.git $branch

if [ $? -eq 0 ]; then
  bash $SCRIPT_FOLDER/get.sh
fi
