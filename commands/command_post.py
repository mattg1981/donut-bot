import random
from datetime import datetime
from pathlib import Path

from web3 import Web3

from database import database
from commands.command import Command
import re


class PostCommand(Command):
    VERSION = 'v0.1.20240503-post'
    COMMENT_SIGNATURE = f'\n\n^(donut-bot {VERSION})'

    def __init__(self, config, reddit):
        super(PostCommand, self).__init__(config, reddit)
        self.command_text = "!post"

    def leave_comment_reply(self, comment, reply):
        reply += self.COMMENT_SIGNATURE
        database.set_processed_content(comment.fullname, Path(__file__).stem)
        comment.reply(reply)

    def process_comment(self, comment):
        self.logger.info(f"process post command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        user = comment.author.name

        # handle `!post status` command

        # there is no default or other 'sub-command' for !post, so I will remove this check
        # if f'{self.command_text} status' in comment.body.lower():

        self.logger.info("  checking status")

        # todo: pass in community

        cooldown_check = database.get_post_cooldown(user, int(self.config["posts"]["post_cooldown_in_minutes"]))
        post_per_day_check = database.get_post_status(user)

        eligible_to_post = True
        next_post_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if post_per_day_check:
            # both cooldown and post per day are in effect, find the max next post to display to the user
            eligible_to_post = False
            next_post_time = post_per_day_check[0]["next_post"]

        if not cooldown_check['eligible_to_post_cooldown']:
            eligible_to_post = False
            next_post_time = max(cooldown_check["next_post"], next_post_time)

        if not eligible_to_post:
            self.logger.info(f"  not currently eligible to post")
            self.leave_comment_reply(comment,
                                     f'**Status**: u/{user} is not currently eligible to post.'
                                     f'\n\n**Current Time**: `{cooldown_check["now"]} UTC`'
                                     f'\n\n**Eligible to Post**: `{next_post_time} UTC`')
            return

        count_result = database.get_post_count_in_last_24h(user)
        self.logger.info("  eligible to post")
        self.leave_comment_reply(comment,
                                 f'**Status**: u/{user} is eligible to post. ({int(self.config["posts"]["max_per_24_hours"]) - int(count_result["count"])} / {int(self.config["posts"]["max_per_24_hours"])} remaining)')

