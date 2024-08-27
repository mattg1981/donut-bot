#!/bin/bash

echo "begin building members file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_special_memberships.py
cp -fr ../temp/members.json ../../memberships/
cd ../../memberships/

echo "git pull"
git pull

echo "git commit..."
git commit -m "updated members.json ${TIMESTAMP_DAY} ${TIMESTAMP}" ./members.json

echo "git push..."
git push

echo "completed successfully"