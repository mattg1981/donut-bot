
import json
import logging
import os
import sqlite3
import praw

from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from datetime import datetime

def update_last_update(user: str, ban_date: datetime, last_updated: datetime) -> None:
    with sqlite3.connect(db_path) as db:
        exists_sql = """
            update bans 
            set last_updated = ?
            where username = ? and ban_date = ?;
        """

        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(exists_sql, [last_updated, user, ban_date])


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
    log_path = os.path.join(base_dir, "../logs/get_bans.log")
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
                         user_agent='ban-bot (by u/mattg1981)')

    with sqlite3.connect(db_path) as db:
        build_table_and_index = """
               CREATE TABLE IF NOT EXISTS bans (
                    id           INTEGER   NOT NULL
                                           PRIMARY KEY AUTOINCREMENT,
                    username     NVARCHAR2 NOT NULL
                                           COLLATE NOCASE,
                    note         NVARCHAR2 NOT NULL,
                    ban_date     DATETIME  NOT NULL,
                    permanent    BOOLEAN   NOT NULL,
                    days_left    INT,
                    community    NVARCHAR2 NOT NULL
                                           COLLATE BINARY,
                    last_updated DATETIME,
                    created_at   DATETIME  NOT NULL
                                           DEFAULT CURRENT_TIMESTAMP
                );

               CREATE UNIQUE INDEX IF NOT EXISTS bans_username_bandate ON bans (
                    username,
                    ban_date
                );
           """
        cur = db.cursor()
        cur.executescript(build_table_and_index)

    logger.info("begin build_ban_list")
    last_updated = datetime.now()
    try:
        for idx, community_token in enumerate(config["community_tokens"]):
            community = community_token["community"]
            if "r/" in community:
                community = community[2:]

            logger.info(f"processing subreddit: [{community}]")

            # these are used for dates to calculate if the ban is overturned
            # we are only returning 200 results from the ban query, so we want to make sure
            # we are only testing bans during that range

            max_ban_date = datetime.fromtimestamp(0)
            min_ban_date = datetime.now()

            for ban in reddit.subreddit(community).banned(limit=200):
                logger.info(f"processing banned user: [{ban.name}]")

                user = ban.name
                ban_date = datetime.fromtimestamp(ban.date)
                note = ban.note
                days_left = ban.days_left
                permanent = ban.days_left is None

                if ban_date < min_ban_date:
                    min_ban_date = ban_date

                if ban_date > max_ban_date:
                    max_ban_date = ban_date

                with sqlite3.connect(db_path) as db:
                    exists_sql = "select * from bans where username = ? and ban_date = ?;"
                    db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                    cursor = db.cursor()
                    cursor.execute(exists_sql, [user, ban_date])
                    exists = cursor.fetchone()

                if exists:
                    update_last_update(user, ban_date, last_updated)
                    logger.info(f"  record previously processed...")
                    continue

                logger.info(f"  new record, add to database...")

                # else, insert this record
                with sqlite3.connect(db_path) as db:
                    insert_ban_sql = """
                        insert into bans (username, note, ban_date, permanent, days_left, community, last_updated)
                        values (?,?,?,?,?,?,?);
                    """

                    db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
                    cursor = db.cursor()
                    cursor.execute(insert_ban_sql, [user, note, ban_date, permanent, days_left, community, last_updated])

        # update any overturned bans
        logger.info("overturning bans...")
        with sqlite3.connect(db_path) as db:
            overturn_ban_sql = """
                    update bans
                    set is_overturned = 1
                    where permanent = 1 
                      and (last_updated is null or last_updated <> ?) 
                      and ban_date between ? and ?
                """

            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = db.cursor()
            cursor.execute(overturn_ban_sql, [last_updated, min_ban_date, max_ban_date])

        logger.info("complete")

    except Exception as e:
        logger.error(e)
