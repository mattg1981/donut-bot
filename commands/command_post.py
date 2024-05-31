import random
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
        if f'{self.command_text} status' in comment.body.lower():
            self.logger.info("  checking status")
            result = database.get_post_status(user)

            if result is None or len(result) == 0:
                self.logger.info("  eligible to post")
                self.leave_comment_reply(comment,
                                         f'**Status**: u/{user} is eligible to post.')
            else:
                self.logger.info("  not currently eligible to post")
                self.leave_comment_reply(comment,
                                         f'**Status**: u/{user} is not currently eligible to post.'
                                         f'\n\n**Current Time**: `{result[0]["now"]} UTC`'
                                         f'\n\n**Eligible to Post**: `{result[0]["next_post"]} UTC`')
            return
