import json
import logging
import time
import praw
import os

from commands import *
from commands.command import Command
from logging.handlers import RotatingFileHandler

if __name__ == '__main__':
    # load config
    config = json.load(open("config.json"))

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("donut_bot")
    logger.setLevel(logging.INFO)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, config["log_path"])
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    client_id = config["reddit_config"]["client_id"]
    client_secret = config["reddit_config"]["client_secret"]
    username = config["reddit_config"]["username"]
    password = config["reddit_config"]["password"]
    user_agent = config["reddit_config"]["user_agent"]

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=client_id,
                         client_secret=client_secret,
                         username=username,
                         password=password,
                         user_agent=user_agent)

    subs = ""
    for sub in config["subreddits"][:-1]:
        subs += sub + "+"
    subs += config["subreddits"][-1]
    subreddits = reddit.subreddit(subs)

    commands = []
    global_objs = list(globals().items())

    for name, obj in global_objs:
        if obj is not Command and isinstance(obj, type) and issubclass(obj, Command):
            commands.append(obj())

    for cls in Command.__subclasses__():
        commands.append(cls())

    # for testing
    # for command in commands:
    #     if command.can_handle("!tip 10 donut"):
    #         command.process_command("!tip 10 donut")
    #         break

    while True:
        for comment in subreddits.stream.comments(pause_after=-1):
            if comment is None:
                time.sleep(6)
            else:
                for command in commands:
                    if command.can_handle(comment):
                        try:
                            command.process_command(comment)
                        except Exception as e:
                            logger.error(e)
                        break


