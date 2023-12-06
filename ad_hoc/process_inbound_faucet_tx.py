import json
import logging
import os
import sqlite3
import urllib.request
import praw

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from datetime import datetime


def notify_user(username, tx_hash, amount):
    logger.info(f"  notifying ::: [user]: {username} [amount]: {amount}  [tx_hash]: {tx_hash}")

    message = (config["inbound_faucet_message"]
               .replace("#NAME#", username)
               .replace("#TX_HASH#", tx_hash)
               .replace("#AMOUNT#", str(amount)))

    # send message
    reddit.redditor(username).message(subject="Faucet Funded!", message=message)

    logger.info("  successfully notified...")
    logger.info("  updating sql processed_at")

    # update sql so we dont process this record again
    with sqlite3.connect(db_path) as db:
        update_sql = """
           update faucet set notified_date = ? where tx_hash = ?
        """
        cursor = db.cursor()
        cursor.execute(update_sql, [datetime.now(), tx_hash])

    logger.info("  successfully updated db... ")

def process_notifications():
    # notify any transactions that need to be notified (if any)
    logger.info("finding transactions that need notifications ...")
    with sqlite3.connect(db_path) as db:
        notify_sql = """
                    SELECT u.username, f.* 
                    from faucet f
                      inner join users u on f.username = u.username
                    where direction = 'INBOUND' and notified_date is null
                """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(notify_sql)
        notifications = cursor.fetchall()

    if not notifications:
        logger.info("  none needed")
    else:
        logger.info(f"  {len(notifications)} found")
    for n in notifications:
        try:
            notify_user(n["username"], n["tx_hash"], n["amount"])
        except Exception as e:
            logger.error(e)

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # locate database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_name = os.path.basename(__file__)[:-3]
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, f"../logs/{log_name}.log")
    file_handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # set up praw
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=os.getenv('REDDIT_USERNAME'),
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent=config["praw_user_agent"])

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute("select max(block) block from faucet where direction = 'INBOUND'")
        starting_block = cursor.fetchone()['block']

    if not starting_block:
        starting_block = 0
    else:
        starting_block = int(starting_block) + 1

    logger.info(f"querying gnosisscan with starting block: {starting_block}...")

    json_result = json.load(urllib.request.urlopen(
        f"https://api.gnosisscan.io/api?module=account&action=txlist&address={config['faucet_wallet_address']}"
        f"&startblock={starting_block}&endblock=99999999&page=1&offset=10000&sort=asc"
        f"&apikey={os.getenv('GNOSIS_SCAN_API_KEY')}"))

    logger.info(f"{len(json_result['result'])} transaction(s) found")

    # no new results
    if not len(json_result['result']):
        process_notifications()
        logger.info("complete.")
        exit(0)

    for tx in json_result['result']:
        logger.info(f"processing tx_hash: {tx['hash']}")

        if tx['from'].lower() == config['faucet_wallet_address'].lower():
            logger.info("outbound transaction, skipping...")
            continue

        address = tx['from']
        amount = float(int(tx['value']) / float(1e18))
        tx_hash = tx['hash']
        block = tx['blockNumber']

        with sqlite3.connect(db_path) as db:
            insert_sql = """
                INSERT INTO faucet (username, address, direction, amount, tx_hash, block, created_date)
                SELECT (select username from users where address =?), ?, 'INBOUND', ?, ?, ?, ?
                WHERE NOT EXISTS (select 1 from faucet where tx_hash = ?)
                RETURNING *
            """
            cursor = db.cursor()
            cursor.execute(insert_sql, [address, address, amount, tx_hash, block, datetime.now(), tx_hash])
            insert_result = cursor.fetchone()

        if not insert_result:
            logger.error(f"failed to insert record for tx_hash: {tx_hash}")
            continue

    process_notifications()

    logger.info('complete.')
