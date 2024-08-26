#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin exporting special memberships ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "get memberships ..."
python3.11 ../ad_hoc/get_memberships.py

echo "export membership data ..."
python3.11 ../ad_hoc/export_memberships.py

cd ../out
cp -fr ./memberships_* ../../donut-bot-output/memberships/

cd ../../donut-bot-output/memberships/

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated memberships ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"