import json
import os.path
import sqlite3
import urllib.request

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

    user_sql = """
            select username, address from users;
        """

    community_memberships = """
        select * from membership_season
        where datetime() between start_date and end_date
         or datetime() >= start_date and end_date is null;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(user_sql)
        registered_users = cursor.fetchall()

        cursor.execute(community_memberships)
        active_seasons = cursor.fetchall()

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))
    if not w3.is_connected():
        exit(4)

    with open('../contracts/membership_abi.json') as abi_file:
        membership_abi = json.load(abi_file)

    current_special_memberships = json.load(urllib.request.urlopen(config["membership"]["members"]))

    special_memberships_out = {}
    if active_seasons:
        # filter to just type == NFT
        special_memberships_out = [sm for sm in current_special_memberships if sm['type'] == "nft"]

    # update special membership access based on NFT
    for season in active_seasons:
        membership_contract = w3.eth.contract(address=w3.to_checksum_address(season["contract_address"]),
                                              abi=membership_abi)

        block = w3.eth.get_block('latest')
        starting_block = block["number"] - 5000

        logs = membership_contract.events.Transfer().get_logs(fromBlock=starting_block)
        # logs = membership_contract.events.Transfer().get_logs(fromBlock=int(season['event_block']) + 1)

        # max_event_block = int(season['event_block'])

        for log in logs:
            owner = log.args['to']
            redditor = next((x["username"] for x in registered_users if x['address'].lower() == log.args['to'].lower()),
                            None)

            record = next((sm for sm in special_memberships_out
                           if int(sm['token_id']) == int(log.args['tokenId'])
                           and sm['season'] == season['season_number']
                           and sm['community'] == season['community']
                           ), None)

            if record:
                # update meta because of a transfer
                record['owner'] = owner
                record['redditor'] = redditor
            else:
                # update meta because of a mint
                membership = {
                    "token_id": log.args['tokenId'],
                    "owner": log.args['to'],
                    "redditor": redditor,
                    "type": "nft",
                    "community": season["community"],
                    "season": season["season_number"],
                }
                special_memberships_out.append(membership)

            # max_event_block = log.blockNumber

        # with sqlite3.connect(db_path) as db:
        #     update_sql = """
        #         update membership_season
        #         set event_block = ?
        #         where id = ?
        #     """
        #     cursor = db.cursor()
        #     cursor.execute(update_sql, [max_event_block, season["id"]])

    if active_seasons:
        # add in special memberships granted by LP activity
        sm_lp = json.load(urllib.request.urlopen(
            "https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/liquidity/liquidity_leaders.json"))

        for lp in [x for x in sm_lp if x['donut_in_lp'] >= config['membership']['donut_count_in_lp']]:
            redditor = next((x["username"] for x in registered_users if x['address'].lower() ==
                             lp['owner'].lower()), None)
            if not redditor:
                continue

            membership = {
                "owner": lp['owner'],
                "redditor": redditor,
                "type": "lp",
                "community": 'all'
            }

            # print(json.dumps(membership))
            special_memberships_out.append(membership)

    out_file = "../temp/members.json"

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(special_memberships_out, f, indent=4)
