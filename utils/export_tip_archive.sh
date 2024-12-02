#!/bin/bash

#
#  moves tip archive files form donut-bot/tip-archive to ../ethtrader-tip-archive and commits the files
#  to the repo
#

echo "begin exporting tip archives ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

cd ../temp
mv -fr * ../../ethtrader-tip-archive

cd ../../ethtrader-tip-archive

echo "git pull"
git pull

echo "git add"
git add --all --force

echo "git commit..."
git commit -m "updated tip archive ${TIMESTAMP_DAY} ${TIMESTAMP}" *

echo "git push..."
git push

echo "completed successfully"