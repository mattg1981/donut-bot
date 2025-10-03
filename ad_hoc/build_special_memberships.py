import json
import os.path
import sqlite3
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from web3 import Web3

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # get all registered users
    user_sql = """
        select username, address from users;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(user_sql)
        registered_users = cursor.fetchall()

    # todo add to config
    contract_addresses = [{
        "community": "EthTrader",
        "address": "0xd6Bf8865375713cFbCc8e941F91eDb3182E783D1"
    }]

    with open('../contracts/membership_abi.json') as abi_file:
        membership_abi = json.load(abi_file)

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))
    if not w3.is_connected():
        print("Failed to connect to INFURA_ARB1_PROVIDER")
        exit(4)

    special_memberships_out = []

    for contract in contract_addresses:
        membership_contract = w3.eth.contract(
            address=w3.to_checksum_address(contract["address"]),
            abi=membership_abi
        )

        # get active memberships
        active = membership_contract.functions.getActiveMemberships().call()

        # iterate the results and add to the output list
        for mintRecord in active:
            token_id = mintRecord[0]
            owner = mintRecord[1]
            created = mintRecord[2]
            expires = mintRecord[3]

            redditor = next((x["username"] for x in registered_users if x['address'].lower() == owner.lower()), None)

            if not redditor:
                continue

            membership = {
                "token_id": token_id,
                "owner": owner,
                "redditor": redditor,
                "created": created,
                "created_string": datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M:%S UTC'),
                "expires": expires,
                "expires_string": datetime.fromtimestamp(expires).strftime('%Y-%m-%d %H:%M:%S UTC'),
                "community": contract["community"],
            }

            special_memberships_out.append(membership)

    out_file = "../temp/members.json"

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(special_memberships_out, f, indent=4)
