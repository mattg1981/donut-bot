#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin building funded accounts output file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "building off-chain tip output file"
python3.11 ../ad_hoc/export_moderators.py

cd ../out
cp -fr ./moderators_* ../../donut-bot-output/moderators/

cd ../../donut-bot-output/

echo "git pull"
git pull

echo "git add (in case a new file is available"
git add --all --force

echo "git commit..."
git commit -m "updated moderators ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"