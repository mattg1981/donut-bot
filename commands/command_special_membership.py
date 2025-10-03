import json
import sqlite3
import urllib.request
from pathlib import Path
from database import database
from datetime import datetime, timedelta
from commands.command import Command

class SpecialMembershipCommand(Command):

    def __init__(self, config, reddit):
        super(SpecialMembershipCommand, self).__init__(config, reddit)
        self.gif_tags = [".gif", ".gifv", "![gif]", "giphy.com", "gfycat.com"]
        self.command_text = ["!membership", *self.gif_tags]
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

        # active_seasons = database.get_active_membership_seasons()
        # if active_seasons:
        if "last_update" not in self.special_membership or datetime.now() - timedelta(minutes=12) >= \
                self.special_membership["last_update"]:
            self.special_membership['last_update'] = datetime.now()
            self.special_membership['members'] = json.load(urllib.request.urlopen(
                "https://raw.githubusercontent.com/EthTrader/memberships/main/members.json"))

        # check if the comment author is a special member
        member = next((m for m in self.special_membership['members']
                       if m['redditor']
                       and m['redditor'].lower() == user.lower()
                       and (m['community'].lower() == community.lower() or m['community'].lower() == 'all')), None)

        if member and "!membership" in comment.body.lower():
            self.leave_comment_reply(comment, f"u/{user}, thank you for being a special member in the "
                                              f"{community} community! Your current membership is valid until {member['expires_string']}.")

        if not member:
            contains_gif = False
            if any(tag in comment.body.lower() for tag in self.gif_tags):
                contains_gif = True

            bot_response = f"[Click here](https://donut-dashboard.com/#/membership) to learn more or to purchase a membership!"

            if contains_gif:
                bot_response = f"Sorry u/{user}, only special members can use GIFs. {bot_response}"
            else:
                bot_response = (f"You are not currently a special member in the {community} community!"
                                f" {bot_response}")

            self.leave_comment_reply(comment, bot_response)

            if contains_gif:
                comment.mod.remove()