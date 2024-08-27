#!/bin/bash

echo "begin building updated liquidity leader file..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

python3.11 ../ad_hoc/build_liquidity_leaders.py
cp -fr ../temp/liquidity_leaders.json ../../donut-bot-output/liquidity/
cd ../../donut-bot-output/liquidity/

echo "git pull"
git pull

echo "git commit..."
git commit -m "updated liquidity_leaders.json ${TIMESTAMP_DAY} ${TIMESTAMP}" ./liquidity_leaders.json

echo "git push..."
git push

echo "completed successfully"