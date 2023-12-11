#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin building funded accounts output file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "building off-chain tip output file"
python3.11 ../ad_hoc/export_funded_accounts.py

cd ../out
cp -fr ./funded_round_* ../../donut-bot-output/funded_accounts/

cd ../../donut-bot-output/

echo "git pull"
git pull

echo "git add (in case a new file is available"
git add --all --force

echo "git commit..."
git commit -m "updated funded accounts output json ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"