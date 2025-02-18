import logging
import os
import time
from logging.handlers import RotatingFileHandler

import praw
from dotenv import load_dotenv

from commands import Command
from config import Config

if __name__ == '__main__':
    # load environment variables from .env file
    load_dotenv()

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("donut_bot")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "logs/donut-bot.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    username = os.getenv('REDDIT_USERNAME')

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=username,
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent='donut-bot (by u/mattg1981)')

    # find all the subs that we are supposed to operate on
    config = Config()
    communities = config.communities
    subs = '+'.join([c.community for c in communities])

    # find all the commands that can process comments
    commands = []
    for c in Command.__subclasses__():
        commands.append(c(config, reddit))

    while True:
        try:
            # for comment in reddit.subreddit(subs).stream.comments(skip_existing=True):
            for comment in reddit.subreddit(subs).stream.comments():
                if not comment.author or comment.author.name == username or comment.author == "EthTrader_Reposter":
                    continue

                # find all commands that can process this comment
                for command in [c for c in commands if c.can_handle(comment)]:
                    try:
                        command.process_comment(comment)
                    except Exception as cmdException:
                        print(f'cmdException: {cmdException}')
        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
