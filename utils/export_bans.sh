#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin exporting bans ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/export_bans.py

echo "exported bans ..."
echo "begin to add bans to repository"

cd ../out
cp -fr ./perm_bans* ../../donut-bot-output/bans/
cp -fr ./temp_bans* ../../donut-bot-output/bans/

cd ../../donut-bot-output/bans/

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated bans ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"