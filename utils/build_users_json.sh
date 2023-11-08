#!/bin/bash

echo "begin building new users.json file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_users_json.py
cp -fr ../temp/users.json ../../donut.distribution/docs/
cd ../../donut.distribution/docs/

echo "git commit..."
git commit -m "updated users.json ${TIMESTAMP_DAY} ${TIMESTAMP_DAY}" ./users.json

echo "git push..."
git push

echo "completed successfully"