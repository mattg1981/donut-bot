import json
import os.path
import urllib.request
import sqlite3

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as conf:
        config = json.load(conf)

    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    out_file = "../temp/liquidity_leaders.json"

    sql = """
        select username, address from users;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(sql)
        registered_users = cursor.fetchall()

    sushi_lp = []

    # get sushi lp position holders
    position_query = """query get_positions($pool_id: ID!) {
              positions(where: {pool: $pool_id}) {
                id
                owner
                liquidity
              }
            }"""

    client = Client(
        transport=RequestsHTTPTransport(
            url='https://api.thegraph.com/subgraphs/name/sushi-v3/v3-arbitrum',
            verify=True,
            retries=5,
        ))

    variables = {"pool_id": config["contracts"]["arb1"]["sushi_pool"]}

    # get pool info for current price
    response = client.execute(gql(position_query), variable_values=variables)

    if len(response['positions']) == 0:
        print("positions not found")
        exit(-1)

    total_pool = 0

    for position in response['positions']:
        if int(position['liquidity']) == 0:
            continue

        total_pool += int(position['liquidity'])

        if position['owner'].lower() == config["contracts"]["arb1"]["multi-sig"].lower():
            user = 'r/EthTrader Multi-Sig Wallet'
        else:
            user = next((u['username'] for u in registered_users if
                         u['address'].lower() == position['owner'].lower()), None)

        existing_owner = next((s for s in sushi_lp if s['owner'].lower() == position['owner']), None)

        if existing_owner:
            # sum up their liquidity
            existing_owner['id'] = f"{existing_owner['id']},{position['id']}"
            existing_owner['liquidity'] = int(existing_owner['liquidity']) + int(position['liquidity'])
        else:
            sushi_lp.append({
                'id': position['id'],
                'owner': position['owner'],
                'liquidity': int(position['liquidity']),
                'user': user
            })

    for s in sushi_lp:
        s['percent_of_pool'] = s['liquidity'] / total_pool * 100

    # do I need to group by user/owner here and sum()? - i'll let the real world data decide

    sushi_lp = sorted(sushi_lp, key=lambda k: k['liquidity'], reverse=True)

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(sushi_lp, f, indent=4)
