import csv
import logging
import os.path
import sqlite3
import requests

from logging.handlers import RotatingFileHandler

DISTRIBUTION_ROUND = 130

if __name__ == '__main__':
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
              inner join users u on fund.from_address = u.address COLLATE NOCASE
            WHERE fund.processed_at BETWEEN 
              (select from_date from distribution_rounds where distribution_round = ?)  and 
              (select to_date from distribution_rounds where distribution_round = ?) 
        """

        tips_sql = """
            SELECT u.username 'from_user', e.* 
            FROM earn2tip e
            INNER JOIN users u on e.from_address = u.address COLLATE NOCASE
            WHERE created_date BETWEEN
              (select from_date from distribution_rounds where distribution_round = ?)  and 
              (select to_date from distribution_rounds where distribution_round = ?) 
              -- AND to_address IS NOT NULL;
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
    # logger.info(f"retrieving final csv file from EthTrader/donut.distribution...")
    # url = f"https://raw.githubusercontent.com/EthTrader/donut.distribution/main/in/round_{DISTRIBUTION_ROUND}.csv"
    # request_result = requests.get(url).text
    # reader = csv.DictReader(request_result.splitlines(), delimiter=',')
    # csv_records = list(reader)

    # get file from the /in directory
    with open(f'../in/round_{DISTRIBUTION_ROUND}.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',')
        csv_records = list(reader)

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

    i = 0
    for tip in tips:
        i = i + 1
        logger.info(
            f"processing tip [{i} of {len(tips)}] << [from]: {tip['from_user']} [to]:{tip['to_user']} [amount]: {tip['amount']} [token]: {tip['token']} >>")

        if not tip["to_address"]:
            logger.info(f"user [{tip['to_user']}] is not registered, tip will be ignored! {tip}")
            logger.info("")
            continue

        from_user = next((x for x in csv_records if x["username"].lower() == tip["from_user"].lower()), None)
        to_user = next((x for x in csv_records if x["username"].lower() == tip["to_user"].lower()), None)

        # add_tippee = False

        if from_user['username'] == 'diarpiiiii':
            pass

        if not from_user or not to_user:
            # either the tipper or the receiver was not in the csv file
            if not from_user:
                logger.warning(f"tipper [{tip['from_user']}] not in csv, tip will not materialize... tip: {tip}")
                continue
            else:
                # will need to add the tippee to the csv_records dict
                # add_tippee = True
                logger.warning(f"tip receiver [{tip['to_user']}] was not in csv, adding now...")
                to_user = {
                    "username": tip["to_user"],
                    "comments": 0,
                    "comment score": 0,
                    "post score": 0,
                    "points": 0,
                    "blockchain_address": tip["to_address"]
                }
                csv_records.append(to_user)

        old_sender_val = from_user['points']
        tip_amount = tip["amount"]

        # user didnt have enough to tip
        if float(old_sender_val) < tip_amount:
            logger.warning(f"user: [{tip['from_user']}] tipped but did not have enough funds to cover the tip [prev balance: {old_sender_val}]")
            tip_amount = float(old_sender_val)
            if tip_amount > 0:
                logger.warning(f"original tip amount: {tip_amount} -> amount materialized: {old_sender_val}")
            else:
                logger.warning(f"no amount materialized")
                continue

        from_user['points'] = float(from_user['points']) - float(tip_amount)
        logger.info(f"[{tip['from_user']}] previous [points]: {old_sender_val} -> new [points]: {from_user['points']}")

        old_recipient_val = to_user['points']
        to_user['points'] = float(to_user['points']) + float(tip_amount)
        logger.info(f"[{tip['to_user']}] previous [points]: {old_recipient_val} -> new [points]: {to_user['points']}")
        logger.info("")

    logger.info("outputting .csv")

    # sort by points
    csv_records.sort(key=lambda x: float(x['points']), reverse=True)

    # write new csv
    with open(f"../out/round_{DISTRIBUTION_ROUND}_with_tip_distribution_and_funding.csv", 'w') as output_file:
        writer = csv.DictWriter(output_file, csv_records[0].keys(), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(csv_records)

    logger.info("complete")
