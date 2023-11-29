import json
import logging
import os
import sqlite3
import urllib.request
from logging.handlers import RotatingFileHandler
from datetime import datetime

from dotenv import load_dotenv
from web3 import Web3

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

    with open(os.path.normpath("../contracts/tipping_contract_abi.json"), 'r') as f:
        tip_abi = json.load(f)

    w3_connected = False
    tipping_contract = None
    gno_w3 = None

    for public_node in config["gno_public_nodes"]:
        try:
            logger.info(f"  trying GNO node {public_node}")
            gno_w3 = Web3(Web3.HTTPProvider(public_node))
            if gno_w3.is_connected():
                w3_connected = True
                tipping_contract = gno_w3.eth.contract(address=Web3.to_checksum_address(config['tipping_contract_address']), abi=tip_abi)
                break
        except Exception as e:
            logger.error(f"  {e}")

    if not w3_connected:
        logger.error(f"  exhausted all public nodes, aborting...")

    with sqlite3.connect(db_path) as db:
        # build the table and index if it is the first run of this application
        build_table_and_index = """
           CREATE TABLE IF NOT EXISTS onchain_tip (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                from_address NVARCHAR2 NOT NULL COLLATE NOCASE,
                to_address NVARCHAR2 NOT NULL COLLATE NOCASE,
                tx_hash NVARCHAR2 NOT NULL COLLATE NOCASE,
                block BIGINT,
                amount DECIMAL(10, 5) NOT NULL,
                token NVARCHAR2 NOT NULL,
                content_id NVARCHAR2,
                timestamp DATETIME NOT NULL,
                created_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
            onchain_tip_tx_hash_idx on onchain_tip(tx_hash);
        """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.executescript(build_table_and_index)
        cursor.execute("select max(block) 'block' from onchain_tip")
        max_block = cursor.fetchone()['block']

    if not max_block:
        max_block = 0

    api_key = os.getenv('GNOSIS_SCAN_IO_API_KEY')
    tippingContract = config["tipping_contract_address"]
    batch = 0
    offsetSize = 10000

    results = []
    while True:
        batch = batch + 1
        results = [x for x in results if x['blockNumber'] != max_block]

        logger.info(f"  querying Gnosis API [batch {batch} , starting from block {max_block}]..")
        url = f"https://api.gnosisscan.io/api?module=account&action=txlist&address={tippingContract}&startblock={max_block}&endblock=99999999&page=1&offset={offsetSize}&sort=asc&apikey={api_key}"

        url_result = json.load(urllib.request.urlopen(url))
        tip_transactions = [x for x in url_result['result']]
        results.extend(tip_transactions)

        logger.info(f"  found {len(tip_transactions)} tips!")

        max_block = max(tip['blockNumber'] for tip in results)

        if len(tip_transactions) < offsetSize:
            break

    # remove errored tips
    results = [x for x in results if x['isError'] != 1]

    # keep only 'tip' methods
    results = [x for x in results if x['methodId'] == '0xeb4e2e5d']

    tips = []
    for result in results:
        # get to_address, token, content_id and amount from the input
        input = tipping_contract.decode_function_input(result['input'])
        to_address = input[1]['_to']
        token_contract_address = input[1]['_token']
        amount = float(int(input[1]['_amount']) / float(1e18))

        content_id_bytes = input[1]["_contentId"]
        content_id = gno_w3.to_text(content_id_bytes.hex()).replace("\x00", "")

        # special case when content_id is not properly written
        if "t3_" not in content_id and "t1_" not in content_id:
            logger.warning(f" direct tip to multisig, tx_hash {result['hash']}")
            content_id = None

        # todo make this a more dynamic lookup
        if token_contract_address.lower() == '0x524b969793a64a602342d89bc2789d43a016b13a':
            token = 'donut'
        else:
            token = token_contract_address

        # map the results to conform to the sql query below keeping just the fields we want
        tips.append((
            result['from'], to_address, result['hash'], result['blockNumber'], amount, token, content_id,
            datetime.fromtimestamp(int(result['timeStamp']))
        ))

    logger.info("saving tips to database")

    # save the tips to db
    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

        sql = """
            insert or replace into onchain_tip (from_address, to_address, tx_hash, block, amount, token, content_id, timestamp)
            values (?,?,?,?,?,?,?,?)
        """

        cursor = db.cursor()
        cursor.executemany(sql, tips)

    logger.info("complete")