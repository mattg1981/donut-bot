import json
import logging
import os
import sqlite3
import urllib.request
from datetime import datetime
from logging.handlers import RotatingFileHandler

import math
import praw
from dotenv import load_dotenv
from web3 import Web3


def notify_user(username, tx_hash, amount, token):
    logger.info(f"notifying ::: [user]: {username} [amount]: {amount} [token]: {token} [tx_hash]: {tx_hash}")

    # create message
    message = (config["account_funded_message"]
               .replace("#NAME#", username)
               .replace("#TX_HASH#", tx_hash)
               .replace("#AMOUNT#", str(amount))
               .replace("#TOKEN#", token))

    logger.info("successfully notified...")

    # send message
    reddit.redditor(username).message(subject="Account Funded!", message=message)

    update_sql = """
       update funded_account set processed_at = ? where tx_hash = ?
    """

    logger.info("updating sql processed_at")

    # update sql so we dont process this record again
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute(update_sql, [datetime.now(), tx_hash])

    logger.info("successfully updated db... ")


def update_settings(max_block):
    logger.info(f'final block: {max_block}')
    logger.info(f'updating db settings...')

    with sqlite3.connect(db_path) as db:
        update_block = """
                UPDATE settings set value = ? where setting = 'funded_account_last_block';
            """

        update_runtime = """
                UPDATE settings set value = ? where setting = 'funded_account_last_runtime';
            """
        cursor = db.cursor()
        cursor.execute(update_block, [max_block])
        cursor.execute(update_runtime, [datetime.now()])


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
        cursor.execute("select value 'block' from settings where setting = 'funded_account_last_block'")
        starting_block = cursor.fetchone()['block']

    starting_block = int(starting_block) + 1
    max_block = starting_block

    logger.info(f"querying gnosisscan with starting block: {starting_block}...")

    json_result = json.load(urllib.request.urlopen(
        f"https://api.gnosisscan.io/api?module=account&action=tokentx&address={config['multi_sig_address']}"
        f"&startblock={starting_block}&endblock=99999999&page=1&offset=10000&sort=asc"
        f"&apikey={os.getenv('GNOSIS_SCAN_API_KEY')}"))

    logger.info(f"{len(json_result['result'])} transaction(s) found")

    # no new results
    if not len(json_result['result']):
        update_settings(max_block)
        logger.info("complete.")
        exit(0)

    valid_tokens = []
    for ct in config["community_tokens"]:
        for token in ct["tokens"]:
            valid_tokens.append(token["contract_address"])

    ignored_addresses = [account["address"] for account in config["funded_accounts_to_ignore"]]

    w3_was_success = False

    for public_node in config["gno_public_nodes"]:
        try:
            if w3_was_success:
                break

            logger.info(f"trying [public_node] {public_node}...")
            w3 = Web3(Web3.HTTPProvider(public_node))
            if w3.is_connected():
                w3_was_success = True
                logger.info("  connected to public node")
            else:
                logger.warning("  failed to connect, try next...")
                continue

            for tx in json_result["result"]:
                max_block = tx["blockNumber"]

                # only concern ourselves with pre-screened/valid tokens
                # and ensure they are not from addresses that should be ignored
                if (tx["contractAddress"] in valid_tokens and tx["from"].lower() not in ignored_addresses
                        and tx["to"].lower() == config['multi_sig_address'].lower()):
                    try:
                        from_address = tx["from"]
                        to_address = tx["to"]
                        token = tx["tokenSymbol"]
                        blockchain_amount = tx["value"]
                        amount = float(tx["value"]) / math.pow(10, float(tx["tokenDecimal"]))
                        block = tx["blockNumber"]
                        timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))
                        tx_hash = tx["hash"]

                        w3_tx = w3.eth.get_transaction(tx_hash)
                        inpt = w3_tx.input.hex()

                        # not a transfer event
                        if not inpt[:10] == "0xa9059cbb":
                            logger.info(f"not a transfer transaction [tx_hash]: {tx_hash}")
                            continue
                        else:
                            logger.info(
                                f"transfer:: [from]: {from_address} [to]: {to_address} [amount]: {amount} [token]: {token} [tx_hash]: {tx_hash}")

                        with sqlite3.connect(db_path) as db:
                            insert_sql = """
                                INSERT INTO funded_account (from_user, from_address, blockchain_amount, amount, token, block_number, tx_hash, tx_timestamp, created_at)
                                SELECT (select username from users where address =?), ?, ?, ?, ?, ?, ?, ?, ?
                                WHERE NOT EXISTS (select 1 from funded_account where tx_hash = ?)
                                RETURNING (select username from users where address = ?)
                            """
                            cursor = db.cursor()
                            cursor.execute(insert_sql, [from_address, blockchain_amount, amount, token, block,
                                                        tx_hash, timestamp, datetime.now(), tx_hash, from_address])
                            sql_result = cursor.fetchone()

                        # user is not registered or we didnt insert because we have already processed
                        # this tx_hash
                        if not sql_result:
                            logger.warning(f"[transaction]: {tx_hash} was not returned from the database to be notified on."
                                           f" this can happen because the user is not registered in our database or because "
                                           f"this transaction is being processed again for some reason.")
                        else:
                            # notify user that we processed their transaction
                            notify_user(sql_result[0], tx_hash, amount, token)

                    except Exception as e:
                        logger.error(e)
        except Exception as e:
            logger.error(e)

    # find previous transactions that need to be notified (if any)
    logger.info("finding old transactions that need notifications ...")
    with sqlite3.connect(db_path) as db:
        notify_sql = """
                SELECT u.username, fa.* from funded_account fa
                inner join users u on fa.from_address = u.address COLLATE NOCASE
                where processed_at is null
            """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(notify_sql)
        notifications = cursor.fetchall()

    if not notifications:
        logger.info("  none needed")
    for n in notifications:
        notify_user(n["username"], n["tx_hash"], n["amount"], n["token"])

    update_settings(max_block)
    logger.info('complete.')
