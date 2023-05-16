#! /bin/bash

## Run on srvubuclt002 with input from Brightspace Data Hub Organizational Units csv (full or diff)
## cat orgunitsdiff-20220904.csv | ./update-orgids.sh

grep Vula | gawk -vFPAT='[^,]*|"[^"]*"' '{print "update migration_site set imported_site_id=" $1 " where transfer_site_id = REPLACE(\"" $5 "\", \"Vula_\", \"\");"}' | mysql tsugi_dev
mysql tsugi_dev -e "update migration_site set state='completed' where state='importing' and imported_site_id is not null"
mysql tsugi_dev -e "select state, count(state) from migration_site group by state"
