import json
import logging
import os
import random
import sys
import urllib.request
import math
import praw

from dotenv import load_dotenv
from web3 import Web3
from datetime import datetime
from decimal import Decimal

from logging.handlers import RotatingFileHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from database import database as db


def send_any_notifications():
    # find previous transactions that need to be notified (if any)
    logger.info("finding transactions that need notifications ...")
    notifications = db.get_funded_accounts_to_notify()

    if not notifications:
        logger.info("  none needed")
    for n in notifications:
        notify_user(n["username"], n["tx_hash"], n["amount"], n["token"])


def notify_user(username, tx_hash, amount, token):
    logger.info(f"notifying ::: [user]: {username} [amount]: {amount} [token]: {token} [tx_hash]: {tx_hash}")

    # create message
    message = (config["account_funded_message"]
               .replace("#NAME#", username)
               .replace("#TX_HASH#", tx_hash)
               .replace("#AMOUNT#", str(amount))
               .replace("#TOKEN#", token))

    # send message
    reddit.redditor(username).message(subject="Account Funded!", message=message)

    logger.info("successfully notified...")
    logger.info("updating sql processed_at")

    db.update_funded_account(tx_hash)

    logger.info("successfully updated db... ")


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

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

    logger.info("begin")

    # set up praw
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=os.getenv('REDDIT_USERNAME'),
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent="r/EthTrader Funded Accounts")

    logger.info("find most recently processed block in the db")
    starting_block = db.get_max_multisig_block()

    if not starting_block:
        starting_block = 0
    else:
        starting_block = int(starting_block) + 1

    logger.info(f"querying arbiscan with starting block: {starting_block}...")

    # json_result = json.load(urllib.request.urlopen(
    #     f"https://api.arbiscan.io/api?module=account&action=tokentx&address={config['contracts']['arb1']['multi-sig']}"
    #     f"&startblock=0&endblock=99999999&page=1&offset=10000&sort=asc"
    #     f"&apikey={os.getenv('ARBISCAN_API_KEY')}"))

    json_result = json.load(urllib.request.urlopen(
        f"https://api.etherscan.io/v2/api?chainid=42161&module=account&action=tokentx&address={config['contracts']['arb1']['multi-sig']}"
        f"&startblock={starting_block}&page=1&offset=10000&sort=asc"
        f"&apikey={os.getenv('ARBISCAN_API_KEY')}"))

    logger.info(f"{len(json_result['result'])} transaction(s) found")

    # no new results
    if not len(json_result['result']):
        send_any_notifications()
        logger.info("complete.")
        exit(0)

    valid_tokens = []
    for ct in config["community_tokens"]:
        for token in ct["tokens"]:
            valid_tokens.append(token["contract_address"].lower())

    ignored_addresses = [account["address"] for account in config["funded_accounts_to_ignore"]]

    w3 = Web3(Web3.HTTPProvider(os.getenv("CHAINSTACK_ARB1_PROVIDER")))

    if not w3.is_connected():
        logger.warning("  failed to connect, try next...")
        exit(4)

    for tx in json_result["result"]:
        # this bug has been corrected and this check should no longer be needed
        # there is a bug with the arbiscan api where if you supply any number > 0 as the starting block it will not
        # return results.  So we request all records and then filter here instead.
        # if int(tx['blockNumber']) < starting_block:
        #     continue

        # only concern ourselves with pre-screened/valid tokens
        # and ensure they are not from addresses that should be ignored
        print(json_result)
        if (tx["contractAddress"].lower() in valid_tokens and tx["from"].lower() not in ignored_addresses
                and tx["to"].lower() == config['contracts']['arb1']['multi-sig'].lower()):

            tx_hash = tx["hash"]
            w3_tx = w3.eth.get_transaction(tx_hash)
            inpt = w3_tx.input.hex()

            # not a transfer event
            if not inpt[:10] == "0xa9059cbb":
                logger.debug(f"not a transfer transaction [tx_hash]: {tx_hash}")
                continue
            else:
                from_address = tx["from"]
                to_address = tx["to"]
                token = tx["tokenSymbol"]
                blockchain_amount = tx["value"]
                amount = Decimal(tx["value"]) / Decimal(math.pow(10, float(tx["tokenDecimal"])))
                block = tx["blockNumber"]
                timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))

                logger.info(
                    f"transfer:: [from]: {from_address} [to]: {to_address} [amount]: {amount} [token]: {token} [tx_hash]: {tx_hash}")

            logger.info("insert record into database...")

            db.insert_funded_account(from_address, amount, token, block, tx_hash, timestamp)

            logger.info("sucess...")

    send_any_notifications()
    logger.info('complete.')
