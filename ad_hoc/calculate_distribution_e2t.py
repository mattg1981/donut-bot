import csv
import json
import logging
import math
import os.path
import random
import sqlite3

from logging.handlers import RotatingFileHandler
from decimal import Decimal
from copy import deepcopy

import requests
from web3 import Web3

DISTRIBUTION_ROUND = 130

if __name__ == '__main__':
    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # locate database
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_name = f"{os.path.basename(__file__)[:-3]}_round_{DISTRIBUTION_ROUND}"
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.INFO)

    log_path = os.path.join(base_dir, f"../logs/{log_name}.log")

    if os.path.exists(log_path):
        os.remove(log_path)

    file_handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # begin logic
    logger.info(f"begin e2t distribution calculation for round: {DISTRIBUTION_ROUND}")

    # get funded accounts
    with sqlite3.connect(db_path) as db:
        funded_account_sql = """
            SELECT u.username, u.address, fund.token, fund.amount, fund.tx_hash 
            FROM funded_account fund 	
              inner join users u on fund.from_user = u.username
            WHERE fund.processed_at BETWEEN 
              (select from_date from distribution_rounds where distribution_round = ?)  and 
              (select to_date from distribution_rounds where distribution_round = ?) ;
        """

        tips_sql = """
            SELECT e.*,
               CASE WHEN u.username IS NULL THEN 0 ELSE 1 END to_user_exists
            FROM earn2tip e
               LEFT JOIN users u ON e.to_user = u.username
            WHERE 
               created_date BETWEEN (
                    SELECT from_date
                      FROM distribution_rounds
                     WHERE distribution_round = ?
                ) AND (
                   SELECT to_date
                     FROM distribution_rounds
                    WHERE distribution_round = ?
               );
        """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        logger.info(f"getting funded accounts from db...")
        cursor.execute(funded_account_sql, [DISTRIBUTION_ROUND, DISTRIBUTION_ROUND])
        funded_accounts = cursor.fetchall()

        logger.info(f"getting tips from db...")
        cursor.execute(tips_sql, [DISTRIBUTION_ROUND, DISTRIBUTION_ROUND])
        tips = cursor.fetchall()

    # get the csv file once it has been published
    logger.info(f"retrieving final csv file from mydonuts.online...")
    url = f"https://www.mydonuts.online/home/mydonuts/static/rounds/round_{DISTRIBUTION_ROUND}.csv"
    request_result = requests.get(url).text
    reader = csv.DictReader(request_result.splitlines(), delimiter=',')
    csv_records = list(reader)

    # get file from the /in directory
    # with open(f'../in/round_{DISTRIBUTION_ROUND}.csv', newline='') as csvfile:
    #     reader = csv.DictReader(csvfile, delimiter=',')
    #     csv_records = list(reader)

    csv_records_original = deepcopy(csv_records)

    logger.info(f"begin applying funded accounts...")

    # apply funded account tokens
    for fa in funded_accounts:
        logger.info(
            f"  processing funded account: [user]: {fa['username']} [amount]: {fa['amount']} [token]: {fa['token']} [tx_hash]: {fa['tx_hash']}")

        record = next((x for x in csv_records if x["username"].lower() == fa["username"].lower()), None)

        if not record:
            logger.warning(f"  user [{fa['username']}] funded account but does not appear in the .csv, adding to file")
            csv_records.append({
                "username": {fa['username']},
                "comments": 0,
                "comment score": 0,
                "post score": 0,
                "points": fa['amount'],
                "blockchain_address": fa['address']
            })
            continue

        old_val = record['points']
        record['points'] = float(record['points']) + float(fa["amount"])
        logger.info(f"  previous [points]: {old_val} -> new [points]: {record['points']}")

    logger.info(f"completed funded accounts")
    logger.info(f"begin applying tips...")

    # store the tips/amounts that actually materialize and we will save it to a file to be used for tip
    # bonus calcs
    materialized_tips = []

    i = 0
    for tip in tips:
        i = i + 1
        logger.info(
            f"processing tip [{i} of {len(tips)}] << [from]: {tip['from_user']} [to]:{tip['to_user']} [amount]: {tip['amount']} [token]: {tip['token']} >>")

        if not tip["to_user_exists"]:
            logger.info(f"user [{tip['to_user']}] is not registered, tip will be ignored! {tip}")
            logger.info("")
            continue

        from_user = next((x for x in csv_records if x["username"].lower() == tip["from_user"].lower()), None)
        to_user = next((x for x in csv_records if x["username"].lower() == tip["to_user"].lower()), None)

        if not from_user or not to_user:
            # either the tipper or the receiver was not in the csv file
            if not from_user:
                logger.warning(f"tipper [{tip['from_user']}] not in csv, tip will not materialize... tip: {tip}")
                continue
            else:
                # will need to add the receiver to the csv_records dict
                logger.warning(f"tip receiver [{tip['to_user']}] was not in csv, adding now...")

                # it is okay that we use tip[to_address] - even though this
                # could be old/stale, it will get updated at the end of the file
                to_user = {
                    "username": tip["to_user"],
                    "comments": 0,
                    "comment score": 0,
                    "post score": 0,
                    "points": 0,
                    "blockchain_address": 0  # will get populated at end of this process
                }
                csv_records.append(to_user)

        old_sender_val = from_user['points']
        tip_amount = tip["amount"]

        # user didn't have enough to tip
        if float(old_sender_val) < tip_amount:
            logger.warning(
                f"user: [{tip['from_user']}] tipped but did not have enough funds to cover the tip [prev balance: {old_sender_val}]")
            tip_amount = float(old_sender_val)
            if tip_amount > 0:
                logger.warning(f"original tip amount: {tip_amount} -> amount materialized: {old_sender_val}")
            else:
                logger.warning(f"no amount materialized")
                logger.warning("")
                continue

        from_user['points'] = float(from_user['points']) - float(tip_amount)
        logger.info(f"[{tip['from_user']}] previous [points]: {old_sender_val} -> new [points]: {from_user['points']}")

        old_recipient_val = to_user['points']
        to_user['points'] = float(to_user['points']) + float(tip_amount)
        logger.info(f"[{tip['to_user']}] previous [points]: {old_recipient_val} -> new [points]: {to_user['points']}")

        materialized_tips.append({
            'from_user': tip['from_user'],
            # 'from_address': tip['from_address'],
            'to_user': tip['to_user'],
            # 'to_address': tip['to_address'],
            'amount': tip_amount,
            'token': tip['token'],
            'content_id': tip['content_id'],
            'parent_content_id': tip['parent_content_id'],
            'submission_content_id': tip['submission_content_id'],
            'community': tip['community'],
            'created_date': tip['created_date']
        })

        logger.info("")

    # update to the latest address for each user, and also expand .ens names
    logger.info("updating to latest user addresses on file and resolving .ens names")
    with sqlite3.connect(db_path) as db:
        latest_address = """
            SELECT address 
            FROM users 
            WHERE username=? ;
        """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()

        for csv_record in csv_records:
            cursor.execute(latest_address, [csv_record['username']])
            user_address = cursor.fetchone()

            if not user_address:
                logger.warning(f"  user [{csv_record['username']}] not found, skip updating address")

            address = user_address['address']
            if ".eth" in address:
                logger.info(
                    f"  resolving ENS address for user [{csv_record['username']}] -> ENS [{user_address['address']}]")

                public_nodes = config["eth_public_nodes"]
                random.shuffle(public_nodes)
                for public_node in public_nodes:
                    try:
                        logger.info(f"  trying ETH node {public_node}...")

                        w3 = Web3(Web3.HTTPProvider(public_node))
                        if w3.is_connected():
                            logger.info("  connected to public node...")

                            # check to verify the ENS address resolves
                            address = w3.ens.address(user_address['address'])
                            logger.info(f"    ENS domain [{user_address['address']}] resolved to [{address}]...")

                            if address is None:
                                logger.warning("  ENS did not resolve...")

                            break
                    except Exception as e:
                        logger.error(e)

            if address != csv_record['blockchain_address']:
                logger.info(
                    f"  user [{csv_record['username']}] updating from address [{csv_record['blockchain_address']}] -> to [{address}]")
                csv_record['blockchain_address'] = address

    # # sort by points
    # logger.info("sorting dataset by points")
    # csv_records.sort(key=lambda x: float(x['points']), reverse=True)

    for original_record in csv_records_original:
        e2t_record = next((x for x in csv_records if x["username"].lower() == original_record["username"].lower()),
                          None)
        original_record["net e2t"] = round(Decimal(e2t_record['points']) - Decimal(original_record['points']), 5)

    logger.info("outputting .csv")
    fieldnames = ["username", "comments", "comment_score", "posts", "post_score", "raw_score", "pay2post", "points",
             "net e2t", "blockchain_address"]

    # write new csv
    with open(f"../out/round_{DISTRIBUTION_ROUND}_adjusted.csv", 'w') as output_file:
        # writer = csv.DictWriter(output_file, csv_records[0].keys(), extrasaction='ignore')
        writer = csv.DictWriter(output_file, fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(csv_records_original)

    logger.info("outputting materialized tips .json")

    # write materialized tips
    materialized_tips_file_output = f"../out/round_{DISTRIBUTION_ROUND}_materialized_tips.json"
    if os.path.exists(materialized_tips_file_output):
        os.remove(materialized_tips_file_output)

    with open(materialized_tips_file_output, 'w') as f:
        json.dump(materialized_tips, f, indent=4)

    logger.info("complete")
