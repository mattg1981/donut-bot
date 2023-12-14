import json
import logging
import os
import sqlite3
import urllib

from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from datetime import datetime, timedelta

from web3 import Web3

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("ban_bot")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/get_special_memberships.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    with open(os.path.normpath("../contracts/eth_membership_abi.json"), 'r') as f:
        eth_membership_abi = json.load(f)

    eth_contract_address = config['eth_membership_address']
    eth_iface = Web3().eth.contract(address=Web3.to_checksum_address(eth_contract_address), abi=eth_membership_abi)

    special_memberships = [
        {
            'network': 'mainnet',
            'url': f"https://api.etherscan.io/api?module=account&action=txlist&address={eth_contract_address}&startblock=0&endblock=99999999&sort=asc&apikey={os.getenv('ETHERSCAN_API_KEY')}",
            'community': 'ethtrader'
        }

    ]

    for sm in special_memberships:
        url_result = json.load(urllib.request.urlopen(sm['url']))
        subscribe_txs = [r for r in url_result['result'] if r['methodId'] == "0x5bb80a5f"]

        subscribers = []
        for tx in subscribe_txs:
            decoded_input = eth_iface.decode_function_input(tx['input'])
            address, weeks = decoded_input[1].values()
            tx_date = datetime.fromtimestamp(int(tx['timeStamp']))
            end_date = tx_date + timedelta(days=weeks * 30)

            existing_author = next((s for s in subscribers if s["address"].lower() == address.lower()), None)

            if existing_author:
                if tx_date > existing_author["expiration_date"]:
                    # previous membership expired - renew it
                    start_date = tx_date
                    existing_author['expiration_date'] = end_date
                else:
                    # extend the membership
                    end_date = existing_author['expiration_date'] + timedelta(days=weeks * 30)

                continue

            subscribers.append({
                'address': address,
                'start_date': tx_date,
                'expiration_date': end_date,
                'network': sm['network'],
                'community': sm['community']
            })
            continue

    created_date = datetime.now()
    sql_subscribers = [(s['address'], s['start_date'], s['expiration_date'], s['community'], s['network'], created_date)
                       for s in subscribers]

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

        insert_sql = """
            insert or replace into special_membership (address, start_date, end_date, community, network, created_date)
            values (?,?,?,?,?,?);
        """

        update_sql = """
            UPDATE special_membership
            SET user = (
                   SELECT username
                     FROM users u
                    WHERE u.address = special_membership.address
            )
            WHERE user IS NULL;
        """

        cursor = db.cursor()
        cursor.executemany(insert_sql, sql_subscribers)
        cursor.execute(update_sql)
