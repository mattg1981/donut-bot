
import json
import logging
import os
import sqlite3
import praw

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from datetime import datetime


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("ban_bot")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/build_ban_list.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('BAN_LIST_CLIENT_ID'),
                         client_secret=os.getenv('BAN_LIST_CLIENT_SECRET'),
                         username=os.getenv('BAN_LIST_USERNAME'),
                         password=os.getenv('BAN_LIST_PASSWORD'),
                         user_agent=config["praw_user_agent_ban_bot"])

    with sqlite3.connect(db_path) as db:
        build_table_and_index = """
               CREATE TABLE IF NOT EXISTS
                 `bans` (
                   `id` integer not null primary key autoincrement,
                   `username` NVARCHAR2 not null,
                   `note` NVARCHAR2 not null,
                   `ban_date` datetime not null,
                   `permanent` BOOLEAN not null,
                   `days_left` int null,
                   `community` NVARCHAR2 not null,
                   `created_at` datetime not null default CURRENT_TIMESTAMP
                 );

               CREATE UNIQUE INDEX IF NOT EXISTS bans_username_bandate ON bans (
                    username,
                    ban_date
                );
           """
        cur = db.cursor()
        cur.executescript(build_table_and_index)

    logger.info("begin build_ban_list")
    try:
        for idx, community_token in enumerate(config["community_tokens"]):
            community = community_token["community"]
            if "r/" in community:
                community = community[2:]

            logger.info(f"processing subreddit: [{community}]")

            for ban in reddit.subreddit(community).banned():
                logger.info(f"processing banned user: [{ban.name}]")

                user = ban.name
                ban_date = datetime.fromtimestamp(ban.date)
                note = ban.note
                days_left = ban.days_left
                permanent = ban.days_left is None

                with sqlite3.connect(db_path) as db:
                    exists_sql = "select * from bans where username = ? and ban_date = ?;"

                    db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                    cursor = db.cursor()
                    cursor.execute(exists_sql, [user, ban_date])
                    exists = cursor.fetchone()

                if exists:
                    logger.info(f"  record previously processed...")
                    break

                logger.info(f"  new record, add to database...")

                # else, insert this record
                with sqlite3.connect(db_path) as db:
                    insert_ban_sql = """
                        insert into bans (username, note, ban_date, permanent, days_left, community)
                        values (?,?,?,?,?,?);
                    """

                    db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                    cursor = db.cursor()
                    cursor.execute(insert_ban_sql, [user, note, ban_date, permanent, days_left, community])

        logger.info("complete")

    except Exception as e:
        logger.error(e)
