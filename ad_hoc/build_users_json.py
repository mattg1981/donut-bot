import json
import os.path
import random
import urllib.request
import sqlite3

from dotenv import load_dotenv
from web3 import Web3


def get_address(address):
    # public_nodes = config["eth_public_nodes"]
    # random.shuffle(public_nodes)
    # for public_node in public_nodes:
    try:
        if '.eth' not in address:
            return w3.to_checksum_address(address)

        if w3.is_connected():
            # dont do any error handling, let the process fail
            eth_address = w3.ens.address(address)
            return eth_address

    except Exception as e:
        print(f"error: {e}")


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as c:
        config = json.load(c)

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ETH_PROVIDER')))

    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    out_file = "../temp/users.json"

    sql = """
    select * from users;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(sql)
        registered_users = cursor.fetchall()

    print(f'{len(user_json)} users currently in users.json')

    for u in registered_users:
        try:
            json_user = next(j for j in user_json if j["username"].lower() == u["username"].lower())
            json_user["address"] = get_address(u["address"])
        except StopIteration as e:
            # not found in the enumerable
            user_json.append({
                "username": u["username"],
                "address": get_address(u["address"]),
                "contrib": 0,
                "donut": 0,
                "weight": 0
            })
        except Exception as e:
            print(e)
            exit(4)

    print(f'{len(user_json)} users now in users.json')

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(user_json, f, indent=4)

    pass
