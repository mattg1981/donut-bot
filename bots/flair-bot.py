import json
import logging
import os
import sqlite3
import time
import types
import urllib.request
import sys
import praw
import hashlib

from pathlib import Path
from web3 import Web3
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from database import database

UNREGISTERED = []
LP_PROVIDERS = {}
SPECIAL_MEMBERS = {}


def display_number(number):
    if 1_000 <= number < 1_000_000:
        return str(round(number / 1_000, 1)) + "K"
    elif number >= 1_000_000:
        return str(round(number / 1_000_000, 2)) + "M"
    elif number >= 1_000_000_000:
        return str(round(number / 1_000_000_000, 2)) + "B"
    elif number >= 1_000_000_000_000:
        return str(round(number / 1_000_000_000_000, 2)) + "T"

    return str(int(number))


def get_onchain_amounts(user_address):
    try:
        # ---- get mainnet balance ----------------
        logger.info(f"  connecting to INFURA_ETH_PROVIDER...")
        eth_w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ETH_PROVIDER')))

        if not eth_w3.is_connected():
            logger.error("failed to connect to INFURA_ETH_PROVIDER")
            raise Exception("failed to connect to INFURA_ETH_PROVIDER")

        if '.eth' in user_address.lower():
            logger.info("  ENS name detected, do lookup...")

            user_address = eth_w3.ens.address(user_address)

            if user_address is None:
                raise Exception(f"ENS did not resolve for {user_address}")
        else:
            user_address = Web3.to_checksum_address(user_address)

        # donut token
        donut_address_eth = '0xC0F9bD5Fa5698B6505F643900FFA515Ea5dF54A9'
        eth_donut_contract = eth_w3.eth.contract(address=eth_w3.to_checksum_address(donut_address_eth), abi=eth_abi)
        eth_token_balance = eth_donut_contract.functions.balanceOf(user_address).call()
        eth_balance = eth_w3.from_wei(eth_token_balance, "ether")

        # ---- get gnosis balance ----------------------
        logger.info(f"  connecting to ANKR_API_PROVIDER")
        gno_w3 = Web3(Web3.HTTPProvider(os.getenv('ANKR_API_PROVIDER')))

        if not gno_w3.is_connected():
            logger.error("failed to connect to ANKR_API_PROVIDER")
            raise Exception("failed to connect to ANKR_API_PROVIDER")

        # donut token
        donut_address_gno = '0x524B969793a64a602342d89BC2789D43a016B13A'
        donut_contract = gno_w3.eth.contract(address=gno_w3.to_checksum_address(donut_address_gno), abi=eth_abi)
        gno_token_balance = donut_contract.functions.balanceOf(user_address).call()
        gno_balance = eth_w3.from_wei(gno_token_balance, "ether")

        # ---- get arb 1 balances ----------------------
        logger.info(f"  connecting to CHAINSTACK_ARB1_PROVIDER")
        arb1_w3 = Web3(Web3.HTTPProvider(os.getenv('CHAINSTACK_ARB1_PROVIDER')))

        if not arb1_w3.is_connected():
            logger.error("failed to connect to CHAINSTACK_ARB1_PROVIDER")
            raise Exception("failed to connect to CHAINSTACK_ARB1_PROVIDER")

        # donut token on ARB1
        donut_address_arb1 = '0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5'
        arb1_donut_contract = arb1_w3.eth.contract(address=arb1_w3.to_checksum_address(donut_address_arb1),
                                                   abi=eth_abi)
        arb1_token_balance = arb1_donut_contract.functions.balanceOf(user_address).call()
        arb1_balance = arb1_w3.from_wei(arb1_token_balance, "ether")

        # contrib information
        contrib_address_arb1 = "0xF28831db80a616dc33A5869f6F689F54ADd5b74C"
        contrib_contract_arb1 = arb1_w3.eth.contract(address=arb1_w3.to_checksum_address(contrib_address_arb1),
                                                     abi=contrib_abi)
        contrib_token_balance_arb1 = contrib_contract_arb1.functions.balanceOf(user_address).call()
        contrib_balance = arb1_w3.from_wei(contrib_token_balance_arb1, "ether")

    except Exception as ex:
        return None

    lp = 0
    try:
        if "last_update" not in LP_PROVIDERS or datetime.now() - timedelta(minutes=20) >= LP_PROVIDERS["last_update"]:
            LP_PROVIDERS['last_update'] = datetime.now()
            LP_PROVIDERS['providers'] = json.load(urllib.request.urlopen(
                "https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/liquidity/liquidity_leaders.json"))

        lp = next(
            (l['percent_of_pool'] for l in LP_PROVIDERS["providers"] if l["owner"].lower() == user_address.lower()),
            None)
    except Exception as ex:
        pass

    ret_val = types.SimpleNamespace()
    ret_val.donuts = int(eth_balance + gno_balance + arb1_balance)
    ret_val.contrib = int(contrib_balance)

    # ret_val.contrib = int(contrib_balance_arb1)
    # ret_val.lp = int(lp_eth + lp_gno)
    # ret_val.stake = int(stake_eth + stake_gno)

    if lp:
        ret_val.lp = lp
    else:
        ret_val.lp = 0

    ret_val.stake = 0
    return ret_val


def set_flair_for_user(fullname, user, community):
    if database.has_processed_content(fullname, Path(__file__).stem) is not None:
        logger.debug("  previously processed...")
        return

    logger.info(f"processing [user]: {user}...")
    logger.debug("  get user from sql...")

    # get address for user
    with sqlite3.connect(db_path) as db:
        registered_sql = """
            select username 
            from users
            where username=?;
        """

        can_update_sql = """
            select username, address, hash, custom_flair, eligible
            from view_flair_can_update 
            where username=?;
        """
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()

        cur.execute(registered_sql, [user])
        registered_lookup = cur.fetchone()

        # dont lookup if user can update flair if they arent registered
        if registered_lookup:
            cur.execute(can_update_sql, [user])
            user_lookup = cur.fetchone()

    if not registered_lookup:
        logger.info(f"  not registered.")
        if user in UNREGISTERED:
            return

        flair_text = "Not Registered"
        UNREGISTERED.append(user)
        reddit.subreddit(community).flair.set(user,
                                         text=flair_text,
                                         css_class="flair-default")
        database.set_processed_content(fullname, Path(__file__).stem)
        return

    special_member_lp = False
    special_member = next((m for m in SPECIAL_MEMBERS['members'] if m['redditor'].lower() == user.lower()
                           and m['type'] == 'lp'), None)

    if special_member:
        special_member_lp = True
    if not special_member:
        special_member = next((m for m in SPECIAL_MEMBERS['members'] if m['redditor'].lower() == user.lower()
                               and m['community'].lower() == community), None)

    if special_member:
        logger.info("  special member...")

    if not user_lookup['eligible'] and not special_member:
        logger.info(f"  not eligible to have their flair updated at this time.")
        database.set_processed_content(fullname, Path(__file__).stem)
        return

    if special_member and user_lookup['custom_flair']:
        flair_text = user_lookup['custom_flair']
    else:
        logger.info(f"get onchain amounts for [user] {user}...")
        result = get_onchain_amounts(user_lookup["address"])

        if not result:
            logger.error(f"  onchain lookup failed, no flair to be applied!")
            return

        flair_text = f":donut: {display_number(result.donuts)} / ⚖️ {display_number(result.contrib)}"

        if result.lp > 0:
            flair_text = flair_text + f" / :sushi: {format(result.lp, '.4f')}%"

    if special_member:
        logger.info("  special member, get flair text from db")

        # remove the special membership icons from the stored text
        flair_text = (flair_text
                      .replace(':lp:', '')
                      .replace(':sm:', '')
                      .strip())

        logger.info(f"  custom_flair -> {flair_text}")

        if special_member_lp:
            flair_text = f":sm: :lp: {flair_text}"
        else:
            # prevent users from using the :lp: emoji if they are not in the LP
            flair_text = f":sm: {flair_text}"

    # use md5 hash instead of built-in python hash to have the same hashes between program restarts
    # flair_hash = hash(flair_text)
    flair_hash = hashlib.md5(flair_text.encode('utf-8')).hexdigest()

    if flair_hash != user_lookup['hash']:
        logger.info(f"  hash lookup -> [db]: {user_lookup['hash']} -- [current]: {flair_hash}")
        logger.info("  setting flair...")
        reddit.subreddit(community).flair.set(user,
                                         text=flair_text,
                                         css_class="flair-default")
    else:
        logger.info("  flair unchanged since last update...")

    logger.info("  update last_update for flair")
    with sqlite3.connect(db_path) as db:
        update_sql = """       
            INSERT OR REPLACE INTO flair (user_id, hash, last_update, custom_flair) 
            VALUES ((select id from users where username=?), ?, ?, ?)
        """
        cur = db.cursor()
        cur.execute(update_sql, [user, flair_hash, datetime.now(), flair_text])

    database.set_processed_content(fullname, Path(__file__).stem)

    logger.info("  success.")


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("flair_bot")

    # set to info for more info - lots of logs are generated
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/flair-bot.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    username = os.getenv('FLAIR_BOT_USERNAME')

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('FLAIR_BOT_CLIENT_ID'),
                         client_secret=os.getenv('FLAIR_BOT_CLIENT_SECRET'),
                         username=username,
                         password=os.getenv('FLAIR_BOT_PASSWORD'),
                         user_agent='flair-bot (by u/mattg1981)')

    subs = ""
    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]
        subs += community
        if idx < len(config["community_tokens"]) - 1:
            subs += '+'

    with open(os.path.normpath("../contracts/donut_mainnet_abi.json"), 'r') as f:
        eth_abi = json.load(f)

    with open(os.path.normpath("../contracts/donut_gnosis_abi.json"), 'r') as f:
        gno_abi = json.load(f)

    with open(os.path.normpath("../contracts/contrib_gnosis_abi.json"), 'r') as f:
        contrib_abi = json.load(f)

    with open(os.path.normpath("../contracts/donut_uniswap_rewards_mainnet_abi.json"), 'r') as f:
        stake_mainnet_abi = json.load(f)

    with open(os.path.normpath("../contracts/donut_uniswap_rewards_gno_abi.json"), 'r') as f:
        stake_gno_abi = json.load(f)

    with open(os.path.normpath("../contracts/uniswap_v2_pair_abi.json"), 'r') as f:
        lp_mainnet_abi = json.load(f)

    with open(os.path.normpath("../contracts/uniswap_v2_pair_gnosis_abi.json"), 'r') as f:
        lp_gno_abi = json.load(f)

    # set flair for community bots once
    reddit.subreddit(subs).flair.update([x for x in config['flair']['ignore']], text='bot',
                                        css_class="flair-default")
    # set verified addresses
    for v in config['flair']['verified']:
        reddit.subreddit(subs).flair.update(v["user"], text=v["text"], css_class=[v["css_class"]])

    ignore_list = [x.lower() for x in config['flair']['ignore']]
    ignore_list.extend([x["user"].lower() for x in config['flair']['verified']])

    # remove the arb1 pioneers flair - but keeping this in to show how to add a custom flair
    # that cannot be changed by users
    # ignore_list.extend([x.lower() for x in config['flair']['arb1-pioneers']])

    while True:
        try:
            if "last_update" not in SPECIAL_MEMBERS or datetime.now() - timedelta(minutes=12) >= SPECIAL_MEMBERS[
                "last_update"]:
                SPECIAL_MEMBERS['last_update'] = datetime.now()
                SPECIAL_MEMBERS['members'] = json.load(urllib.request.urlopen(config['membership']['members']))

            for submission in reddit.subreddit(subs).stream.submissions(pause_after=-1):
                if submission is None:
                    break

                if not submission.author or submission.author.name == username:
                    continue

                if submission.author.name.lower() in ignore_list:
                    continue

                set_flair_for_user(submission.fullname, submission.author.name,
                                   submission.subreddit.display_name.lower())

            for comment in reddit.subreddit(subs).stream.comments(pause_after=-1):
                if comment is None:
                    break

                if not comment.author or comment.author.name == username:
                    continue

                if comment.author.name.lower() in ignore_list:
                    continue

                set_flair_for_user(comment.fullname, comment.author.name, comment.subreddit.display_name.lower())

            time.sleep(10)

        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
