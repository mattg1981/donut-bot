import json
import sqlite3
import urllib.request
from pathlib import Path
from database import database
from datetime import datetime, timedelta
from commands.command import Command

class GifCommand(Command):

    def __init__(self, config, reddit):
        super(GifCommand, self).__init__(config, reddit)
        self.command_text = [".gif", ".gifv", "![gif]", "giphy.com", "gfycat.com"]
        self.special_membership = {}

    def can_handle(self, comment):
        for item in self.command_text:
            if item.lower() in comment.lower():
                return True

        return False

    def leave_comment_reply(self, comment, reply):
        database.set_processed_content(comment.fullname, Path(__file__).stem)
        comment.reply(reply)

    def process_comment(self, comment):
        self.logger.info(f"process post command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        user = comment.author.name
        community = comment.subreddit.display_name.lower()

        active_seasons = database.get_active_membership_seasons()
        if active_seasons:
            if "last_update" not in self.special_membership or datetime.now() - timedelta(minutes=12) >= \
                    self.special_membership["last_update"]:
                self.special_membership['last_update'] = datetime.now()
                self.special_membership['members'] = json.load(urllib.request.urlopen(
                    "https://raw.githubusercontent.com/EthTrader/memberships/main/members.json"))

            # todo: test if any of the `active_seasons` are this current sub

            member = next((m for m in self.special_membership['members']
                           if m['redditor']
                           and m['redditor'].lower() == user.lower()
                           and (m['community'] == community or m['community'] == 'all')), None)

            if not member:
                self.leave_comment_reply(comment, f"Sorry u/{user}, only special members can use GIFs.\n\n"
                                                  f"[Click here](https://donut-dashboard.com/#/membership) to learn more"
                                                  f" or to purchase a membership!")
                comment.mod.remove()