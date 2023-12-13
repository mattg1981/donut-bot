#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin exporting distribution rounds ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/export_distribution_rounds.py

cd ../out
cp -fr ./distribution_round_* ../../donut-bot-output/distribution_rounds/

cd ../../donut-bot-output/distribution_rounds

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated distribution rounds ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"