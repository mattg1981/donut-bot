import json
import logging
import os
import praw

from commands import *
from commands.command import Command
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("donut_bot")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, config["log_path"])
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    username = os.getenv('REDDIT_USERNAME')

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=username,
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent=config["praw_user_agent"])

    subs = ""
    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community=community[2:]
        subs += community
        if idx < len(config["community_tokens"]) - 1:
            subs += '+'

    commands = []
    global_objs = list(globals().items())

    for obj in global_objs:
        if obj is not Command and isinstance(obj, type) and issubclass(obj, Command):
            commands.append(obj())

    for cls in Command.__subclasses__():
        commands.append(cls(config))

    while True:
        # for comment in reddit.subreddits(subs).stream.comments(pause_after=-1):
        for comment in reddit.subreddits(subs).stream.comments():
            if comment.author.name == username:
                continue

            # if using pause_after, uncomment the code below
            # if comment is None:
            #     time.sleep(5)

            # find any command that can handle this comment and then process that comment
            for command in commands:
                if command.can_handle(comment.body):
                    try:
                        command.process_comment(comment)

                        # no point trying the other commands to handle this comment
                        break
                    except Exception as e:
                        logger.error(f'  Exception: {e}')
