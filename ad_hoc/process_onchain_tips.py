import json
import logging
import os
import sqlite3
import urllib.request
from logging.handlers import RotatingFileHandler
from datetime import datetime

from dotenv import load_dotenv

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
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute("select max(block) 'block' from onchain_tip")
        max_block = cursor.fetchone()['block']

    if not max_block:
        max_block = 0 # 30400000

    #  handle edge case where the last update may have returned > 10,000 records.
    #  If we remove and re-add the last block, we can ensure that we will grab all tips in the block.
    #  (unless a single block had more than 10,000 tips in it - very unlikely)
    if max_block > 0:
        with sqlite3.connect(db_path) as db:
            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = db.cursor()
            cursor.execute("delete from onchain_tip where block = ?", [max_block])

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

        max_block = max(tip['blockNumber'] for tip in results)

        if len(tip_transactions) < offsetSize:
            break

    # remove errored tips
    results = [x for x in results if x['isError'] != 1]

    # keep only 'tip' methods
    results = [x for x in results if x['methodId'] == '0xeb4e2e5d']

    # map the results to confirm to the sql query below
    tips = []
    for result in results:
        amount = 0
        content_id = ''
        token_contract_address = ''
        to_address = ''

        # get to_address, token, content_id and amount from the input

        # todo make this a more dynamic lookup
        if token_contract_address.lower() == '0x524b969793a64a602342d89bc2789d43a016b13a':
            token = 'donut'
        else:
            token = token_contract_address

        # keep just the fields we want
        tips.append((
            result['from'], to_address, result['hash'], result['blockNumber'], amount, token, content_id,
            datetime.fromtimestamp(int(result['timeStamp']))
        ))

    # save the tips to db
    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

        sql = """
            insert into onchain_tip (from_address, to_address, tx_hash, block, amount, token, content_id, timestamp)
            values (?,?,?,?,?,?,?,?)
        """

        cursor = db.cursor()
        cursor.executemany(sql, tips)
