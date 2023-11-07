#!/bin/bash

echo "creating backup of donut-bot.db..."
if [ -e database/donut-bot.db ]; then
  TIMESTAMP_DAY=$( date +%Y_%m_%d )
  TIMESTAMP_TIME=$( date +%H )
  TIMESTAMP=$( date +%Y_%m_%d_%H_%M_%S )

  BACKUP_PATH=../database/backups/$TIMESTAMP_DAY/$TIMESTAMP_TIME

  mkdir -p $BACKUP_PATH
  sqlite3 ../database/donut-bot.db ".backup '../${BACKUP_PATH}/donut-bot_${TIMESTAMP}.db'"
fi

#echo "completed successfully"