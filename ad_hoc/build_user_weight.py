import json
import os.path
import random
import sys
import time
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
    sushi_lp_donuts = sum([int(s["tokens"]) for s in lp_providers if s["owner"].lower() == address.lower()])
    return w3_arb.from_wei(arb1_donut_balance, "ether") + sushi_lp_donuts


def get_sushi_providers():
    lp_providers = []
    liquidity = json.load(urllib.request.urlopen("https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/"
                                                 "liquidity/liquidity_leaders.json"))

    for liq in liquidity:
        lp_providers.append({
            "id": liq["id"],
            "owner": liq["owner"],
            "tokens": liq['donut_in_lp']
        })

    return lp_providers


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

    # used for debugging
    # user_json = [{
    #     "username": "DBRiMatt",
    #     "address": "0xFEdD14d3a32FaAbfbd6E290fAA73Aec58e894650",
    #     "contrib": 110710,
    #     "donut": 24079,
    #     "weight": 24079
    # }]

    print('process users')
    count = 0
    for u in user_json:
        count += 1
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

        # getting a http 429 code, so we need to self throttle
        time.sleep(.75)

    if os.path.exists(out_file):
        os.remove(out_file)

    with open(out_file, 'w') as f:
        json.dump(user_json, f, indent=4)

    pass
