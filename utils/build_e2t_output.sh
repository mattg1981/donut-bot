#!/bin/bash

#
#  outputs tip information, commits the file and pushes
#

echo "begin building e2t output file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

echo "associating any unregistered tips"
python3.11 ../ad_hoc/associate_unregistered_tips.py

echo "applying tips and funded accounts"
python3.11 ../ad_hoc/calculate_distribution_e2t.py

cd ../out
cp -fr ./round*.csv ../../donut-bot-output/distribution_data/
cp -fr ./*_materialized_tips.json ../../donut-bot-output/offchain_tips/materialized/

cd ../logs
cp -fr ./calculate_distribution_e2t* ../../donut-bot-output/logs/

cd ../../donut-bot-output/

echo "git pull"
git pull

echo "git add (in case a new file is available"
git add --all --force

echo "git commit..."
git commit -m "applied e2t tips ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"