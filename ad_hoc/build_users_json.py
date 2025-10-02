import json
import os.path
import random
import urllib.request
import sqlite3

from dotenv import load_dotenv
from web3 import Web3

from database import database


def get_address(address):
    if '.eth' not in address.lower():
        return w3.to_checksum_address(address)
    else:
        eth_address = w3.ens.address(address)
        return eth_address


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as c:
        config = json.load(c)

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ETH_PROVIDER')))
    if not w3.is_connected():
        print('w3 failed to connect...')
        exit(4)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))

    ### download registration details from the dao website
    dao_user_json = json.load(urllib.request.urlopen("https://donut-dao-registration-submissions.s3.us-east-2.amazonaws.com/data/new-users.json"))

    for dao_user in dao_user_json:
        # check if user exists in the database already
        db_user_exists = database.get_user_by_name(dao_user["username"])

        if db_user_exists:
            # do not update the address if they exist.  this is a safety precaution to prevent someone
            # from trying to maliciously change the wallet address using the dao website.  to prevent this,
            # the dao website can only be used for NEW registrations.
            print(f"user from donutdao.org json file already exists [{dao_user['username']}], skipping...")
            continue
        else:
            print(f'add user from donutdao.org json file: [{dao_user["username"]}]')
            database.insert_or_update_address(dao_user["username"], dao_user["wallet"], 'dao')


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
