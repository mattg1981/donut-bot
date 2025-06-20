#!/bin/bash

#
#  outputs raw potd data, commits the file and pushes
#

echo "begin exporting raw potd ..."
TIMESTAMP_DAY=$( date +%Y/%m/%d )
TIMESTAMP=$( date +%H:%M )

cd ../database
rm potd_raw.json
sqlite3 donut-bot.db '.mode json' '.once potd_raw.json' 'select * from potd;'

echo "exported raw potd entries ..."
echo "begin to add raw potd to repository"

mv -f potd_raw.json ~/donut-bot-output/posts/potd_raw.json
cd ~/donut-bot-output/posts/
git pull
git add --all --force
git commit -m "updated raw potd entries ${TIMESTAMP_DAY} ${TIMESTAMP}" *
git push

echo "completed successfully"