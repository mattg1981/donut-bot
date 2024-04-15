import json
import os.path
import random
import sys
import urllib.request
import sqlite3

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from web3 import Web3


def calc_mainnet_donut(address):
    eth_donut_balance = donut_eth_contract.functions.balanceOf(address).call()
    staked_mainnet_balance = staking_eth_contract.functions.balanceOf(
        address).call() * mainnet_multiplier
    return w3_eth.from_wei(eth_donut_balance + staked_mainnet_balance, "ether")


def calc_gno_donut(address):
    gno_donut_balance = donut_gno_contract.functions.balanceOf(address).call()
    staked_gno_balance = staking_gno_contract.functions.balanceOf(address).call() * gno_multiplier
    return w3_gno.from_wei(gno_donut_balance + staked_gno_balance, "ether")


def calc_arb_donut(address, lp_providers):
    arb1_donut_balance = donut_arb1_contract.functions.balanceOf(address).call()
    sushi_lp_donuts = sum([int(s["tokens"]) for s in sushi_lp if s["owner"].lower() == address.lower()])
    return w3_arb.from_wei(arb1_donut_balance + sushi_lp_donuts, "ether")


def get_sushi_providers():
    lp_providers = []

    # get sushi lp position holders
    position_query = """query get_positions($pool_id: ID!) {
                  positions(where: {pool: $pool_id}) {
                    id
                    owner
                    liquidity
                    tickLower { tickIdx }
                    tickUpper { tickIdx }
                    pool { id }
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

    # return the tick and the sqrt of the current price
    pool_query = """query get_pools($pool_id: ID!) {
                  pools(where: {id: $pool_id}) {
                    tick
                    sqrtPrice
                  }
                }"""

    client = Client(
        transport=RequestsHTTPTransport(
            url='https://api.thegraph.com/subgraphs/name/sushi-v3/v3-arbitrum',
            verify=True,
            retries=5,
        ))

    variables = {"pool_id": config["contracts"]["arb1"]["lp"]}

    # get pool info for current price
    response = client.execute(gql(pool_query), variable_values=variables)

    if len(response['pools']) == 0:
        print("position not found")
        exit(-1)

    pool = response['pools'][0]
    current_tick = int(pool["tick"])
    current_sqrt_price = int(pool["sqrtPrice"]) / (2 ** 96)

    # get position info in pool
    response = client.execute(gql(position_query), variable_values=variables)

    if len(response['positions']) == 0:
        print("position not found")
        exit(-1)

    for position in response['positions']:
        liquidity = int(position["liquidity"])
        tick_lower = int(position["tickLower"]["tickIdx"])
        tick_upper = int(position["tickUpper"]["tickIdx"])
        pool_id = position["pool"]["id"]

        token0 = position["token0"]["symbol"]
        token1 = position["token1"]["symbol"]
        decimals0 = int(position["token0"]["decimals"])
        decimals1 = int(position["token1"]["decimals"])

        # Compute and print the current price
        current_price = tick_to_price(current_tick)
        adjusted_current_price = current_price / (10 ** (decimals1 - decimals0))

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

        # print info about the position
        adjusted_amount0 = amount0  # / (10 ** decimals0)
        adjusted_amount1 = amount1  # / (10 ** decimals1)

        lp_providers.append({
            "id": position["id"],
            "owner": position["owner"],
            "tokens": adjusted_amount1
        })

    return lp_providers


def tick_to_price(tick):
    tick_base = 1.0001
    return tick_base ** tick


def calculate_staking_mulitpliers():
    global mainnet_multiplier, gno_multiplier

    was_success = False
    for j in range(1, 8):
        try:
            eth_lp_supply = lp_eth_contract.functions.totalSupply().call()
            gno_lp_supply = lp_gno_contract.functions.totalSupply().call()

            uniswap_eth_donuts = lp_eth_contract.functions.getReserves().call()
            uniswap_gno_donuts = lp_gno_contract.functions.getReserves().call()

            mainnet_multiplier = uniswap_eth_donuts[0] / eth_lp_supply
            gno_multiplier = uniswap_gno_donuts[0] / gno_lp_supply

            was_success = True
            break
        except Exception as e:
            print(e)
            continue
    if not was_success:
        print("  unable to query at this time, attempt at a later time...")
        exit(4)


def setup_abi_and_contracts():
    global w3_eth, w3_gno, w3_arb, f, contrib_contract, donut_eth_contract, donut_gno_contract, donut_arb1_contract, \
        staking_eth_contract, staking_gno_contract, lp_gno_contract, lp_eth_contract

    w3_eth = Web3(Web3.HTTPProvider(os.getenv('INFURA_ETH_PROVIDER')))
    if not w3_eth.is_connected():
        print('INFURA_ETH_PROVIDER failed to connect...')
        exit(4)

    w3_gno = Web3(Web3.HTTPProvider(os.getenv('ANKR_API_PROVIDER')))
    if not w3_gno.is_connected():
        print('ANKR_API_PROVIDER failed to connect...')
        exit(4)

    w3_arb = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))
    if not w3_gno.is_connected():
        print('INFURA_ARB1_PROVIDER failed to connect...')
        exit(4)

    # load abi's
    with open(os.path.normpath("../contracts/contrib_gnosis_abi.json"), 'r') as f:
        contrib_abi = json.load(f)
    with open(os.path.normpath("../contracts/donut_mainnet_abi.json"), 'r') as f:
        donut_abi = json.load(f)
    with open(os.path.normpath("../contracts/donut_uniswap_rewards_mainnet_abi.json"), 'r') as f:
        staking_abi = json.load(f)
    with open(os.path.normpath("../contracts/uniswap_v2_pair_abi.json"), 'r') as f:
        uniswap_abi = json.load(f)

    # contract objects
    contrib_contract = w3_arb.eth.contract(address=w3_arb.to_checksum_address(config['contracts']['arb1']['contrib']),
                                           abi=contrib_abi)
    donut_eth_contract = w3_eth.eth.contract(address=w3_eth.to_checksum_address(config["contracts"]["mainnet"]
                                                                                ["donut"]), abi=donut_abi)
    donut_gno_contract = w3_gno.eth.contract(address=w3_gno.to_checksum_address(config["contracts"]["gnosis"]
                                                                                ["donut"]), abi=donut_abi)
    donut_arb1_contract = w3_arb.eth.contract(address=w3_arb.to_checksum_address(config["contracts"]["arb1"]
                                                                                 ["donut"]), abi=donut_abi)
    staking_eth_contract = w3_eth.eth.contract(address=w3_eth.to_checksum_address(config["contracts"]["mainnet"]
                                                                                  ["staking"]), abi=staking_abi)
    staking_gno_contract = w3_gno.eth.contract(address=w3_gno.to_checksum_address(config["contracts"]["gnosis"]
                                                                                  ["staking"]), abi=staking_abi)
    lp_gno_contract = w3_gno.eth.contract(address=w3_gno.to_checksum_address(
        config["contracts"]["gnosis"]["lp"]), abi=uniswap_abi)
    lp_eth_contract = w3_eth.eth.contract(address=w3_eth.to_checksum_address(
        config["contracts"]["mainnet"]["lp"]), abi=uniswap_abi)


if __name__ == '__main__':
    print('begin...')

    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as c:
        config = json.load(c)

    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))
    out_file = "../temp/users.json"

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    print('setup abi and contract objects')
    setup_abi_and_contracts()

    print('calculate staking multipliers')
    calculate_staking_mulitpliers()

    print('finding all sushi lp providers')
    sushi_lp = get_sushi_providers()

    print('process users')
    for u in user_json:
        print(f"processing user {u['username']}")

        user_address = u["address"]

        contrib_token_balance_arb1 = contrib_contract.functions.balanceOf(user_address).call()
        contrib = int(w3_arb.from_wei(contrib_token_balance_arb1, "ether"))
        u["contrib"] = contrib

        # calculate donut
        eth_donuts = int(calc_mainnet_donut(user_address))
        gno_donuts = int(calc_gno_donut(user_address))
        arb_donuts = int(calc_arb_donut(user_address, sushi_lp))
        total_donut = eth_donuts + gno_donuts + arb_donuts
        u["donut"] = total_donut

        # weight
        weight = min(contrib, total_donut)
        u["weight"] = weight

        print(f" contrib: [{contrib}] - donut: [{total_donut}] (eth: {eth_donuts}, gno: {gno_donuts}, arb1: {arb_donuts}) - weight: [{weight}]")

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(user_json, f, indent=4)

    pass
