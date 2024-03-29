import json
import logging
import os
import random
import sqlite3
import urllib.request
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from datetime import datetime
from time import strftime, localtime

from dotenv import load_dotenv
from web3 import Web3

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

    with sqlite3.connect(db_path) as db:
        # build the table and index if it is the first run of this application
        build_table_and_index = """
           CREATE TABLE IF NOT EXISTS onchain_tip (
                id           INTEGER         NOT NULL
                                             PRIMARY KEY AUTOINCREMENT,
                from_address NVARCHAR2       NOT NULL
                                             COLLATE NOCASE,
                to_address   NVARCHAR2       NOT NULL
                                             COLLATE NOCASE,
                chain_id     INTEGER,
                tx_hash      NVARCHAR2       NOT NULL
                                             COLLATE NOCASE,
                block        BIGINT,
                amount       DECIMAL (10, 5) NOT NULL,
                token        NVARCHAR2       NOT NULL,
                content_id   NVARCHAR2,
                timestamp    DATETIME        NOT NULL,
                created_date DATETIME        NOT NULL
                                             DEFAULT CURRENT_TIMESTAMP
            );

        CREATE UNIQUE INDEX IF NOT EXISTS chain_id__tx_hash ON onchain_tip (
                chain_id,
                tx_hash
            );


        """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.executescript(build_table_and_index)
        cursor.execute("select max(block) 'block' from onchain_tip where chain_id = 42161")
        max_block = cursor.fetchone()['block']

    if not max_block:
        max_block = 0

    with open(os.path.normpath("../contracts/tipping_contract_abi.json"), 'r') as f:
        tip_abi = json.load(f)

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))
    tipping_contract = w3.eth.contract(address=Web3.to_checksum_address(ARB1_TIPPING_CONTRACT), abi=tip_abi)

    if not w3.is_connected():
        exit(4)

    tips = []
    events = tipping_contract.events.Tip().get_logs(fromBlock=max_block+1)
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

        content_id = w3.to_text(event.args["contentId"].hex()).replace("\x00", "")
        # special case when content_id is not properly written
        if "t3_" not in content_id and "t1_" not in content_id:
            logger.warning(f" direct tip to multisig, tx_hash {tx_hash}")
            content_id = None

        if event.args["token"] == "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5":
            token = "donut"
        else:
            token = event.args["token"]

        # 42161 hardcoded below is arb 1 chain_id
        tips.append((
            from_address, to_address, tx_hash, 42161, block, amount, token, content_id,
            datetime.fromtimestamp(timestamp)
        ))

    logger.info("saving tips to database")

    # save the tips to db
    with sqlite3.connect(db_path) as db:
        def adapt_decimal(d):
            return str(d)

        sqlite3.register_adapter(Decimal, adapt_decimal)

        sql = """
            insert or replace into onchain_tip (from_address, to_address, tx_hash, chain_id, block, amount, token, content_id, timestamp)
            values (?,?,?,?,?,?,?,?,?)
        """

        cursor = db.cursor()
        cursor.executemany(sql, tips)

    logger.info("complete")