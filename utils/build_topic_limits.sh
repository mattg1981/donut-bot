#!/bin/bash

echo "begin building updated liquidity leader file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_topic_limiting.py
cp -fr ../temp/topic_limits.json ../../topic-limiting/
cd ../../topic-limiting/

echo "git pull"
git pull

echo "git commit..."
git commit -m "updated topic_limits.json ${TIMESTAMP_DAY} ${TIMESTAMP}" ./topic_limits.json

echo "git push..."
git push

echo "completed successfully"