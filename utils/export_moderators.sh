#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin exporting moderators ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "get moderators ..."
python3.11 ../ad_hoc/get_moderators.py
python3.11 ../ad_hoc/export_moderators.py

cd ../out
cp -fr ./moderators_* ../../donut-bot-output/moderators/

cd ../../donut-bot-output/moderators/

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated moderators ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"