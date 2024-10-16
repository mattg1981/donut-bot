import json
import logging
import os
import random
import sqlite3
import sys
import urllib.request
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from datetime import datetime
from time import strftime, localtime
from urllib import request

import praw
from dotenv import load_dotenv
from web3 import Web3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from database import database

ARB1_TIPPING_CONTRACT = "0x403EB731A37cf9e41d72b9A97aE6311ab44bE7b9"
ARB1_DONUT = "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5"

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

    # create a reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=os.getenv('REDDIT_USERNAME'),
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent='donut-bot (by u/mattg1981)')

    with open(os.path.normpath("../contracts/tipping_contract_abi.json"), 'r') as f:
        tip_abi = json.load(f)

    w3 = Web3(Web3.HTTPProvider(os.getenv('CHAINSTACK_ARB1_PROVIDER')))
    tipping_contract = w3.eth.contract(address=Web3.to_checksum_address(ARB1_TIPPING_CONTRACT), abi=tip_abi)

    if not w3.is_connected():
        exit(4)

    block = w3.eth.get_block('latest')
    starting_block = block["number"] - 100

    tips = []
    events = tipping_contract.events.Tip().get_logs(fromBlock=starting_block)

    if not events:
        exit(0)

    print("tips detected, grabbing users.json file...")
    users = json.load(request.urlopen(f"https://ethtrader.github.io/donut.distribution/users.json"))

    for event in events:
        receipt = w3.eth.get_transaction_receipt(event.transactionHash)

        if not receipt['status']:
            continue

        block = event.blockNumber
        tx_hash = event.transactionHash.hex()
        timestamp = w3.eth.get_block(event.blockNumber).timestamp
        from_address = event.args["from"]
        to_address = event.args["to"]
        amount = w3.from_wei(int(event.args["amount"]), "ether")

        user = next((u for u in users if u['address'].lower() == from_address.lower()), None)
        if not user or int(amount) < 1:
            weight = 0
        else:
            weight = round(min(int(user['weight']) / config['comment2vote']['max_weight'], 1.0), 4)

        content_id = w3.to_text(event.args["contentId"].hex()).replace("\x00", "")

        # special case when content_id is not properly written
        if "t3_" not in content_id and "t1_" not in content_id:
            logger.warning(f" direct tip to multisig, tx_hash {tx_hash}")
            content_id = None

        if event.args["token"] == config["contracts"]["arb1"]["donut"]:
            token = "donut"

            # todo change to 'in community_tokens' - then copy the logic over to off-chain tips
        else:
            token = event.args["token"]

        # 42161 hardcoded below is arb 1 chain_id
        tips.append((
            from_address, to_address, tx_hash, 42161, block, amount, token, content_id,
            datetime.fromtimestamp(timestamp), weight
        ))

    if not tips:
        logger.info("No tips found")
        exit(0)

    logger.info("notify about new tips")

    sig = f'\n\n^(donut-bot v0.1.20240411-onchain-tip)'

    content_id_index = 7
    from_address_index = 0
    to_address_index = 1
    amount_index = 5
    token_index = 6
    tx_hash_index = 2

    for tip in tips:
        if 't1_' in tip[content_id_index]:
            # get the submission that the comment was made on
            submission_id = reddit.comment(tip[content_id_index]).submission.fullname
            tip_thread_id = database.get_comment_thread_for_submission(submission_id)
        else:
            tip_thread_id = database.get_comment_thread_for_submission(tip[content_id_index])

        sender = next((u for u in users if u['address'] == tip[from_address_index]), None)
        receiver = next((u for u in users if u['address'] == tip[to_address_index]), None)

        if sender and receiver:
            reply = f"u/{sender['username']} has tipped u/{receiver['username']} {round(float(tip[amount_index]), 5)} {tip[token_index]}"
            link = f"https://arbiscan.io/tx/{tip[tx_hash_index]}"
            reply += f'\n\n[LINK (arbiscan.io)]({link})' + sig

            if tip_thread_id:
                tip_thread = reddit.comment(tip_thread_id)
            elif 't1_' in tip[content_id_index]:
                tip_thread = reddit.submission(submission_id)
            else:
                tip_thread = reddit.comment(tip[content_id_index])

            tip_thread.reply(reply)

    logger.info("saving tips to database")

    # save the tips to db
    with sqlite3.connect(db_path) as db:
        def adapt_decimal(d):
            return str(d)

        sqlite3.register_adapter(Decimal, adapt_decimal)

        sql = """
            insert or replace into onchain_tip (from_address, to_address, tx_hash, chain_id, block, amount, 
            token, content_id, timestamp, weight) values (?,?,?,?,?,?,?,?,?,?)
        """

        cursor = db.cursor()
        cursor.executemany(sql, tips)

    logger.info("complete")