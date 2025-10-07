import json
import logging
import os.path
import sqlite3

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

TICK_BASE = 1.0001


def tick_to_price(tick):
    return TICK_BASE ** tick


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as conf:
        config = json.load(conf)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("build_liquidity_leaders")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/liquidity_leaders.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    out_file = "../temp/liquidity_leaders.json"

    sql = """
        select username, address from users;
    """

    logger.info(f"begin")
    logger.info(f"get users from sql...")

    try:
        with sqlite3.connect(db_path) as db:
            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = db.cursor()
            cursor.execute(sql)
            registered_users = cursor.fetchall()

        sushi_lp = []

        # return the tick and the sqrt of the current price
        pool_query = """query get_pools($pool_id: ID!) {
          pools(where: {id: $pool_id}) {
            tick
            sqrtPrice
          }
        }"""

        client = Client(
            transport=RequestsHTTPTransport(
                url=f'https://gateway-arbitrum.network.thegraph.com/api/{os.getenv("GRAPH_API_KEY")}/subgraphs/id/96EYD64NqmnFxMELu2QLWB95gqCmA9N96ssYsZfFiYHg',
                verify=True,
                retries=5,
            ))

        variables = {"pool_id": config["contracts"]["arb1"]["sushi_pool"]}

        logger.info(f"query the graph for pool information...")

        # get pool info for current price
        response = client.execute(gql(pool_query), variable_values=variables)

        if len(response['pools']) == 0:
            logger.error("no pools found, exit...")
            exit(-1)

        pool = response['pools'][0]
        current_tick = int(pool["tick"])
        current_sqrt_price = int(pool["sqrtPrice"]) / (2 ** 96)

        positions = []
        batch_size = 1000
        total_pool = 0

        logger.info(f"query the graph for positions in pool...")

        for itr in range(1, 100_000):
            # get sushi lp position holders
            position_query = """query get_positions($pool_id: ID!, $first: Int!, $skip: Int!) {
                  positions(first: $first, skip: $skip, where: {pool: $pool_id}) {
                    id
                    owner
                    liquidity
                    tickLower { tickIdx }
                    tickUpper { tickIdx }
                    token0 {
                      symbol
                      decimals
                    }
                    token1 {
                      symbol
                      decimals
                    }
                  }
                }"""

            variables = {
                "pool_id": config["contracts"]["arb1"]["sushi_pool"],
                "first": batch_size,
                "skip": batch_size * (itr - 1)
            }

            logger.info(f"  batch {itr}")
            response = client.execute(gql(position_query), variable_values=variables)

            if len(response['positions']) == 0:
                logger.error("positions not found, exiting")
                exit(-1)

            positions.extend(response['positions'])

            if len(response['positions']) < batch_size:
                break

        logger.info(f"{len(positions)} positions found")
        logger.info("calculate position details...")

        for position in positions:
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

        for s in sushi_lp:
            s['percent_of_pool'] = s['liquidity'] / total_pool * 100

        sushi_lp = sorted(sushi_lp, key=lambda k: k['liquidity'], reverse=True)

        logger.info("done...")

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump(sushi_lp, f, indent=4)
    except Exception as e:
        logger.error(e)
        exit(-1)
