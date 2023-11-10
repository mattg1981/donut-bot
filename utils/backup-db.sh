#!/bin/bash

#
#  creates a backup of the donut-bot database using the sqlite3 .backup command
#  and stores it in a folder that is outside of the project
#

if [ -e ../database/donut-bot.db ]; then
  echo "creating backup of donut-bot.db..."
  TIMESTAMP_DAY=$( date +%Y_%m_%d )
  TIMESTAMP_TIME=$( date +%H )
  TIMESTAMP=$( date +%Y_%m_%d_%H_%M_%S )

  # create folder if it doesnt exist
  if [ ! -d ../../donut-bot-db-backups ]; then
    mkdir -p ../../donut-bot-db-backups
  fi

  BACKUP_PATH=../../donut-bot-db-backups/$TIMESTAMP_DAY/$TIMESTAMP_TIME

  mkdir -p $BACKUP_PATH
  sqlite3 ../database/donut-bot.db ".backup '${BACKUP_PATH}/donut-bot_${TIMESTAMP}.db'"
  echo "completed successfully"
else
  echo "database not found... aborting"
fi
