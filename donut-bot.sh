#!/bin/bash

LS_STATUS="$( systemctl is-active litestream )"
if [ "$LS_STATUS" != "active" ]; then
  echo "litestream replication not running, starting ..."
  systemctl start litestream
fi

LS_STATUS=$( systemctl is-active litestream )
if [ "$LS_STATUS" != "active" ]; then
  echo "litestream replication failed to start, exiting ..."
  exit 4
fi

echo "start donut-bot..."
nohup python3.11 main.py > nohup.log 2>&1 &
echo $! > pid.txt

echo "donut-bot is now running..."

echo "start flair-bot..."
cd bots
nohup python3.11 flair-bot.py > flair.nohup 2>&1 &
echo $! > flair.pid

echo "flair-bot is now running..."