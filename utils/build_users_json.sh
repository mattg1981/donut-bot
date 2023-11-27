#!/bin/bash

#
#  grabs the existing users.json from donut.distribution (the system of record)
#  and merges in new register data.  Then it overwrites the file in the donut.distribution
#  directory, commits the file and pushes it to the repository
#
#  PREREQUISITES:
#   ensure that you have cloned the https://github.com/EthTrader/donut.distribution.git project
#   and it resides in the same directory as donut-bot
#

echo "begin building new users.json file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_users_json.py
cp -fr ../temp/users.json ../../donut.distribution/docs/
cd ../../donut.distribution/docs/

echo "git pull"
git pull

echo "git commit..."
git commit -m "updated users.json ${TIMESTAMP_DAY} ${TIMESTAMP}" ./users.json

echo "git push..."
git push

echo "completed successfully"