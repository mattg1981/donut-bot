
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
    log_path = os.path.join(base_dir, "../logs/build_mod_list.log")
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
                         user_agent='moderator-bot (by u/mattg1981)')

    logger.info("begin build_moderator_list")
    update_date = datetime.now()

    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]

        logger.info(f"processing subreddit: [{community}]")

        for mod in reddit.subreddit(community).moderator():
            logger.info(f"processing moderator: [{mod}]")
            user = mod.name
            assigned_date = datetime.fromtimestamp(mod.date)

            with sqlite3.connect(db_path) as db:
                select_sql = """
                    select * from moderators where name = ? and date_assigned = ? and community = ?;
                """

                insert_sql = """
                    INSERT INTO moderators (name, date_assigned, last_update, community) 
                    VALUES (?, ?, ?, ?);
                """

                update_sql = """
                    update moderators 
                    set last_update = ? 
                    where community = ? and name = ? and date_assigned = ?; 
                """
                cursor = db.cursor()
                cursor.execute(select_sql, [user, assigned_date, community])
                select_result = cursor.fetchone()

                if not select_result:
                    cursor.execute(insert_sql, [user, assigned_date, update_date, community])
                else:
                    cursor.execute(update_sql, [update_date, community, user, assigned_date])

        with sqlite3.connect(db_path) as db:
            update_sql = """
                update moderators 
                set is_active = 0 
                where community = ? and last_update <> ?;
            """

            cursor = db.cursor()
            cursor.execute(update_sql, [community, update_date])
            select_result = cursor.fetchone()

        logger.info("complete")