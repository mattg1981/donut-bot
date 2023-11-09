#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin building new users.json file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "associating any unregistered tips"
python3.11 ../ad_hoc/associate_unregistered_tips.py

echo "building tip output file"
python3.11 ../ad_hoc/build_tips_output.py

cd ../out

echo "git add (in case a new file is available"
git add . --force

echo "git commit..."
git commit -m "updated tips output json ${TIMESTAMP_DAY} ${TIMESTAMP_DAY}" *

echo "git push..."
git push

echo "completed successfully"