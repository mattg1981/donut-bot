#!/bin/bash

echo "begin building new users.json file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_users_json.py
cp -fr ../temp/users.json ../../donut-bot-output/liquidity/
cd ../../donut-bot-output/liquidity/

echo "git pull"
git pull

echo "git commit..."
git commit -m "updated liquidity_leaders.json ${TIMESTAMP_DAY} ${TIMESTAMP}" ./users.json

echo "git push..."
git push

echo "completed successfully"