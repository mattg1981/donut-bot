PID=$( cat pid.txt )

if ps -p $PID > /dev/null
then
   echo "donut-bot is running, stopping process..."
   kill -9 $PID
fi

echo "stopping database replication..."
systemctl stop litestream

echo "creating backup of donut-bot.db..."
TIMESTAMP=$( date +%Y_%m_%d_%H_%M_%S )
BACKUP_PATH=database/backups/$TIMESTAMP
mkdir -p $BACKUP_PATH
cp database/donut-bot.db $BACKUP_PATH

echo "pulling down new application code..."
git reset --hard
git pull

echo "restoring donut-bot from replicated database..."
rm database/donut-bot.db
litestream restore -o database/donut-bot.db home/ubu/donut-bot/database/donut-bot.db

echo "restarting database replication..."
sudo systemctl start litestream

echo "marking donut-bot.sh as executable..."
chmod +x donut-bot.sh

echo "completed successfully"