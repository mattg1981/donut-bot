import csv
import json
import os.path
import sqlite3
import time

from dotenv import load_dotenv
from web3 import Web3

TICK_BASE = 1.0001


def tick_to_price(tick):
    return TICK_BASE ** tick


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    sql = """
            select username, address from users;
        """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(sql)
        registered_users = cursor.fetchall()

    w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))
    if not w3.is_connected():
        exit(4)

    with open('../contracts/sushi_position_manager_abi.json') as abi_file:
        nft_abi = json.load(abi_file)

    with open('../contracts/sushi_pool_abi.json') as abi_file:
        pool_abi = json.load(abi_file)

    nft_contract = w3.eth.contract(address=w3.to_checksum_address(config['contracts']['arb1']['sushi_nft_manager']),
                                   abi=nft_abi)

    pool_contract = w3.eth.contract(address=w3.to_checksum_address(config['contracts']['arb1']['sushi_pool']),
                                    abi=pool_abi)

    slot0 = pool_contract.functions.slot0().call()
    current_sqrt_price = int(slot0[0]) / (2 ** 96)
    current_tick = slot0[1]

    total_supply = int(nft_contract.functions.totalSupply().call())
    max_idx = int(nft_contract.functions.tokenByIndex(total_supply - 1).call())

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()

        cursor.execute("select value from settings where setting = 'liquidity_max_idx'")
        start_idx = int(cursor.fetchone()['value'])

        cursor.execute('select nft_id from liquidity_positions;')
        positions = cursor.fetchall()

    liquidity_positions = []
    sushi_lp = []
    donut_address = config['contracts']['arb1']['donut'].lower().strip()

    # find all the ids we need to look up (all the ones saved in the database + any newly minted ones (which we will
    # check to see if its in the pool))
    ids = [p['nft_id'] for p in positions]
    ids.extend(range(start_idx, start_idx + (max_idx - start_idx)))

    for i in ids:
        token_id = i # + start_idx

        print(f"token {token_id}")

        try:
            position = nft_contract.functions.positions(token_id).call()
        except:
            print(f"token {token_id} not found")
            continue

        token0 = position[2]
        token1 = position[3]
        tick_lower = position[5]
        tick_upper = position[6]
        liquidity = position[7]

        if token0.lower() == donut_address or token1.lower() == donut_address:
            print(f"  in the eth/donut pool...")

            if liquidity <= 0:
                print(f"  no liquidity")

                # no liquidity but the nft still exists and a position can be built against it in the future
                liquidity_positions.append({
                    "id": token_id,
                    "liquidity": liquidity
                })

                continue

            owner = nft_contract.functions.ownerOf(token_id).call()

            liquidity_positions.append({
                "id": token_id,
                "owner": owner,
                "liquidity": liquidity,
                "tickLower": {
                    "tickIdx": tick_lower
                },
                "tickUpper": {
                    "tickIdx": tick_upper
                },
                "pool": config["contracts"]["arb1"]["sushi_pool"],
                "token0": {
                    "symbol": "WETH",
                    "decimals": "18"
                },
                "token1": {
                    "symbol": "DONUT",
                    "decimals": "18"
                }
            })

        # self throttle
        # time.sleep(1)

    with sqlite3.connect(db_path) as db:
        sql_setting = '''
            UPDATE settings set value = ? where setting = 'liquidity_max_idx'
        '''

        cursor = db.cursor()
        cursor.execute(sql_setting, [max_idx])

    new_positions = [lp for lp in liquidity_positions if lp['id'] > start_idx]
    for np in new_positions:
        with sqlite3.connect(db_path) as db:
            sql = '''
                insert into liquidity_positions(nft_id)
                SELECT (select ?)
                WHERE NOT EXISTS (select 1 from liquidity_positions where nft_id = ?)
            '''
            cursor = db.cursor()
            cursor.execute(sql, [np['id'], np['id']])

    total_pool = 0
    for position in liquidity_positions:
        if int(position['liquidity']) == 0:
            continue

        total_pool += int(position['liquidity'])

        # calculate holdings
        liquidity = int(position["liquidity"])
        tick_lower = int(position["tickLower"]["tickIdx"])
        tick_upper = int(position["tickUpper"]["tickIdx"])
        decimals0 = int(position["token0"]["decimals"])
        decimals1 = int(position["token1"]["decimals"])
        current_price = tick_to_price(current_tick)
        sa = tick_to_price(tick_lower / 2)
        sb = tick_to_price(tick_upper / 2)

        if tick_upper <= current_tick:
            # Only token1 locked
            amount0 = 0
            amount1 = liquidity * (sb - sa)
        elif tick_lower < current_tick < tick_upper:
            # Both tokens present
            amount0 = liquidity * (sb - current_sqrt_price) / (current_sqrt_price * sb)
            amount1 = liquidity * (current_sqrt_price - sa)
        else:
            # Only token0 locked
            amount0 = liquidity * (sb - sa) / (sa * sb)
            amount1 = 0

        eth_in_lp = amount0 / (10 ** decimals0)
        donut_in_lp = amount1 / (10 ** decimals1)

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
            existing_owner['eth_in_lp'] = existing_owner['eth_in_lp'] + eth_in_lp
            existing_owner['donut_in_lp'] = existing_owner['donut_in_lp'] + donut_in_lp
        else:
            sushi_lp.append({
                'id': position['id'],
                'owner': position['owner'],
                'liquidity': int(position['liquidity']),
                'user': user,
                "eth_in_lp": eth_in_lp,
                "donut_in_lp": donut_in_lp
            })

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute(sql)
        registered_users = cursor.fetchall()

    out_file = "../temp/liquidity_leaders.json"

    for s in sushi_lp:
        s['percent_of_pool'] = s['liquidity'] / total_pool * 100

    sushi_lp = sorted(sushi_lp, key=lambda k: k['liquidity'], reverse=True)

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(sushi_lp, f, indent=4)