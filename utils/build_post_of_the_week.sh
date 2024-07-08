#!/bin/bash

echo "begin building post of the week files..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_weekly_potd.py
cp -fr ../temp/potd* ../../donut-bot-output/posts/
cd ../../donut-bot-output/posts/

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "update potd ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"