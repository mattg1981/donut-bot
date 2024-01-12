import json
import logging
import os
import random
import sqlite3
import time
import types
from datetime import datetime
from decimal import Decimal

import praw
from web3 import Web3

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


def create_post_meta(submission):
    logger.info(f"processing submission: {submission.fullname}")

    is_daily = False
    # determine if it is the daily
    if "daily general discussion" in submission.title.lower():
        is_daily = True

    with sqlite3.connect(db_path) as db:
        sql = """
            SELECT id from post where submission_id = ?;
        """
        cursor = db.cursor()
        cursor.execute(sql, [submission.fullname])
        exists = cursor.fetchone()

    if exists:
        logger.info(f"  submission meta exists - return.")
        return

    logger.info(f"  submission does not exist...")

    comment_thread_id = None
    if not is_daily:
        onchain_link = f"https://www.donut.finance/tip/?action=tip&contentId={submission.fullname}"
        reply_message = f"[Tip this post.]({onchain_link})\n\n"
        reply_message += "Offchain tip confirmations below.\n\n"

        logger.info(f"  send reply...")
        reply = submission.reply(reply_message)

        logger.info(f"  distinguish comment...")
        reply.mod.distinguish(sticky=True)
        comment_thread_id = reply.fullname

    logger.info(f"  store meta in db...")

    author = submission.author
    if submission.author:
        author = submission.author.name


    with sqlite3.connect(db_path) as db:
        sql = """
            INSERT INTO post (submission_id, tip_comment_id, author, is_daily)
            VALUES (?, ?, ?, ?);
        """
        cursor = db.cursor()
        cursor.execute(sql, [submission.fullname, comment_thread_id, author, is_daily])

    logger.info(f"  done.")


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("post_bot")

    # set to info for more info - lots of logs are generated
    logger.setLevel(logging.WARNING)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/post-bot.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    username = os.getenv('REDDIT_USERNAME')

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=username,
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent=config["praw_user_agent_post_bot"])

    subs = ""
    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]
        subs += community
        if idx < len(config["community_tokens"]) - 1:
            subs += '+'

    with sqlite3.connect(db_path) as db:
        build_table_and_index = """
            CREATE TABLE IF NOT EXISTS
              post (
                id             INTEGER   NOT NULL
                                         PRIMARY KEY AUTOINCREMENT,
                submission_id  NVARCHAR2 NOT NULL
                                         COLLATE NOCASE,
                tip_comment_id NVARCHAR2 COLLATE NOCASE,
                author         NVARCHAR2 COLLATE NOCASE,
                is_daily       BOOLEAN   DEFAULT (0),
                created_date   DATETIME  NOT NULL
                                         DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS
              idx_unique_post_submission_id ON post (
                    submission_id
                );
        """
        cur = db.cursor()
        cur.executescript(build_table_and_index)

    while True:
        try:
            for submission in reddit.subreddit(subs).stream.submissions(skip_existing=True):
                if submission is None:
                    continue

                create_post_meta(submission)

        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
