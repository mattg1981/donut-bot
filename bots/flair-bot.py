import json
import logging
import os
import sqlite3
import time
import types
from datetime import datetime, timedelta
import urllib.request

import praw
from web3 import Web3

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

UNREGISTERED = []
LP_PROVIDERS = {}

def display_number(number):
    if 1000 <= number < 1000000:
        return str(round(number / 1000, 1)) + "K"
    elif number >= 1000000:
        return str(round(number / 1000000, 2)) + "M"
    elif number >= 1000000000:
        return str(round(number / 1000000000, 2)) + "B"
    elif number >= 1000000000000:
        return str(round(number / 1000000000000, 2)) + "T"

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

        # lp information
        # lp_address_eth = '0x718Dd8B743ea19d71BDb4Cb48BB984b73a65cE06'
        # lp_eth_contract = eth_w3.eth.contract(address=eth_w3.to_checksum_address(lp_address_eth), abi=lp_mainnet_abi)
        # lp_token_balance = lp_eth_contract.functions.balanceOf(user_address).call()
        # lp_eth = Decimal(lp_token_balance) / Decimal(10 ** 18)

        # stake information
        # stake_address_eth = '0x813fd5A7B6f6d792Bf9c03BBF02Ec3F08C9f98B2'
        # stake_eth_contract = eth_w3.eth.contract(address=eth_w3.to_checksum_address(stake_address_eth), abi=stake_mainnet_abi)
        # stake_token_balance = stake_eth_contract.functions.balanceOf(user_address).call()
        # stake_eth = Decimal(stake_token_balance) / Decimal(10 ** 18)

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

        # lp information
        # lp_address_gno = '0x077240a400b1740C8cD6f73DEa37DA1F703D8c00'
        # lp_gno_contract = gno_w3.eth.contract(address=gno_w3.to_checksum_address(lp_address_gno), abi=lp_gno_abi)
        # lp_token_balance = lp_gno_contract.functions.balanceOf(user_address).call()
        # lp_gno = Decimal(lp_token_balance) / Decimal(10 ** 18)

        # staking information
        # stake_address_gno = '0x84b427415A23bFB57Eb94a0dB6a818EB63E2429D'
        # stake_contract_gno = gno_w3.eth.contract(address=gno_w3.to_checksum_address(stake_address_gno), abi=stake_gno_abi)
        # gno_stake_balance = stake_contract_gno.functions.balanceOf(user_address).call()
        # stake_gno = Decimal(gno_stake_balance) / Decimal(10 ** 18)

        # ---- get arb 1 balances ----------------------
        logger.info(f"  connecting to INFURA_ARB1_PROVIDER")
        arb1_w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ARB1_PROVIDER')))

        if not arb1_w3.is_connected():
            logger.error("failed to connect to INFURA_ARB1_PROVIDER")
            raise Exception("failed to connect to INFURA_ARB1_PROVIDER")

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
            LP_PROVIDERS['providers'] = json.load(urllib.request.urlopen("https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/liquidity/liquidity_leaders.json"))

        lp = next((l['percent_of_pool'] for l in LP_PROVIDERS["providers"] if l["owner"].lower() == user_address.lower()), None)
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


def set_flair_for_user(user):
    logger.debug(f"processing [user]: {user}...")
    logger.debug("  get user from sql...")

    # get address for user
    with sqlite3.connect(db_path) as db:
        registered_sql = """
            select username 
            from users
            where username=?;
        """

        can_update_sql = """
            select username, address, hash
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
        logger.debug(f"  not registered.")
        if user in UNREGISTERED:
            return

        flair_text = "Not Registered"
        UNREGISTERED.append(user)
        reddit.subreddit(subs).flair.set(user,
                                         text=flair_text,
                                         css_class="flair-default")
        return

    if not user_lookup:
        logger.debug(f"  not eligible to have their flair updated at this time.")
        return

    ##
    # TODO: check special membership here ...
    ##

    logger.info(f"get onchain amounts for [user] {user}...")
    result = get_onchain_amounts(user_lookup["address"])

    if not result:
        logger.error(f"  onchain lookup failed, no flair to be applied!")
        return

    flair_text = f":donut: {display_number(result.donuts)} | ⚖️ {display_number(result.contrib)}"

    if result.lp > 0:
        flair_text = flair_text + f" | :sushi: {format(result.lp, '.4f')}%"

    if result.stake > 0:
        flair_text = flair_text + f" | 🥩 {display_number(result.stake)}"

    flair_hash = hash(flair_text)

    if flair_hash != user_lookup['hash']:
        logger.info(f"  hash lookup | [db]: {user_lookup['hash']} -- [current]: {flair_hash}")
        logger.info("  setting flair...")
        reddit.subreddit(subs).flair.set(user,
                                         text=flair_text,
                                         css_class="flair-default")
    else:
        logger.info("  flair unchanged since last update...")

    logger.debug("  update last_update for flair")
    with sqlite3.connect(db_path) as db:
        update_sql = """       
            INSERT OR REPLACE INTO flair (user_id, hash, last_update) 
            VALUES ((select id from users where username=?), ?, ?)
        """
        cur = db.cursor()
        cur.execute(update_sql, [user, flair_hash, datetime.now()])

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

    with sqlite3.connect(db_path) as db:
        build_table_and_index = """
            CREATE TABLE IF NOT EXISTS
              `flair` (
                `id` integer not null primary key autoincrement,
                `user_id` int not null,
                `last_update` DATETIME not null,
                `created_at` datetime not null default CURRENT_TIMESTAMP
              );
              
            CREATE UNIQUE INDEX IF NOT EXISTS
               flair_user_id_idx on flair(user_id);
               
            CREATE VIEW IF NOT EXISTS view_flair_can_update (
                username,
                address,
                hash,
                last_update
            )
            AS
                SELECT u.username,
                       u.address,
                       f.hash,
                       f.last_update
                  FROM users u
                       LEFT JOIN
                       flair f ON u.id = f.user_id
                 WHERE f.last_update IS NULL OR 
                       f.last_update <= Datetime('now', '-30 minutes', 'localtime');
        """
        cur = db.cursor()
        cur.executescript(build_table_and_index)

    # set flair for community bots once
    reddit.subreddit(subs).flair.update([x for x in config['flair']['ignore']], text='bot',
                                        css_class="flair-default")
    # set verified addresses
    for v in config['flair']['verified']:
        reddit.subreddit(subs).flair.update(v["user"], text=v["text"], css_class=[v["css_class"]])

    ignore_list = [x.lower() for x in config['flair']['ignore']]
    ignore_list.extend([x["user"].lower() for x in config['flair']['verified']])
    ignore_list.extend([x.lower() for x in config['flair']['arb1-pioneers']])

    while True:
        try:
            for submission in reddit.subreddit(subs).stream.submissions(pause_after=-1):
                if submission is None:
                    break

                if not submission.author or submission.author.name == username:
                    continue

                if submission.author.name.lower() in ignore_list:
                    continue

                set_flair_for_user(submission.author.name)

            for comment in reddit.subreddit(subs).stream.comments(pause_after=-1):
                if comment is None:
                    break

                if not comment.author or comment.author.name == username:
                    continue

                if comment.author.name.lower() in ignore_list:
                    continue

                set_flair_for_user(comment.author.name)

            time.sleep(10)

        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
