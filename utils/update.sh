#!/bin/bash

PID=$( cat ../pid.txt )

if ps -p $PID > /dev/null; then
   echo "donut-bot is running, stopping process..."
   kill -9 $PID
else
   echo "donut-bot not running..."
fi

#LS_STATUS="$(systemctl is-active litestream)"
#if [ "$LS_STATUS" == "active" ]; then
#  echo "litestream replication is running, stopping ..."
#  systemctl stop litestream
#else
#  echo "litestream replication not running, ok ..."
#fi

echo "creating database backup..."
./backup-db.sh

echo "pulling down new application code..."
cd ..
git reset --hard
git pull

#if [ -e ../database/donut-bot.db ]; then
#  echo "removing existing donut-bot.db"
#  rm ../database/donut-bot.db
#fi
#
#echo "restoring donut-bot from replicated database..."
#cd ../database
#litestream restore -o donut-bot.db donut-bot.db
#cd ..

#echo "restarting database replication..."
#sudo systemctl start litestream

echo "chmoding scripts to executable..."
chmod +x donut-bot.sh
chmod +x utils/*

echo "completed successfully"
echo "starting donut-bot..."
./donut-bot.sh