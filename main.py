import logging
import os
import time
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

from commands import Command
from config import Config
from reddit.reddit_api import RedditAPI

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

    # find all the subs that we are supposed to operate on
    config = Config()
    subs = '+'.join([c.name for c in config.communities])

    # find all the commands that can process comments
    commands = []
    for cls in Command.__subclasses__():
        commands.append(cls())

    # x = is_eligible_to_cast_vote('mattg1981', 't3_1dsfsaz', 'ethtrader')

    while True:
        try:
            # for comment in reddit.subreddit(subs).stream.comments(skip_existing=True):
            for comment in RedditAPI().instance.subreddit(subs).stream.comments():

                # find the community config for the community this comment was posted in
                community = next((c for c in config.communities if c.name.lower() ==
                                          comment.subreddit.display_name.lower()), None)

                if not community:
                    continue  # should never happen

                if not comment.author:
                    continue  # very rare but has previously occurred

                if comment.author in community.ignore:
                    continue  # ignore comments by certain individuals/bots

                # find all commands that can process this comment
                for command in [c for c in commands if c.can_handle(comment)]:
                    try:
                        command.process(comment, community)
                    except Exception as cmdException:
                        logger.error(f'cmdException: {cmdException}')
        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
