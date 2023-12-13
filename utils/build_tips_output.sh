#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin building tips output file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

#echo "associating any unregistered tips"
#python3.11 ../ad_hoc/associate_unregistered_tips.py

echo "building off-chain tip output file"
python3.11 ../ad_hoc/build_tips_output.py

echo "building on-chain tip output file"
python3.11 ../ad_hoc/export_onchain_tips.py

cd ../out
cp -fr ./tips_round_* ../../donut-bot-output/offchain_tips/
cp -fr ./onchain_tips.csv ../../donut-bot-output/onchain_tips

cd ../../donut-bot-output/

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated tips output json ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"