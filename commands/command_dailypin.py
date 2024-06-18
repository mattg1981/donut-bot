import json
import time
import urllib.request
from pathlib import Path


from database import database
from commands.command import Command


class DailyPinCommand(Command):

    def __init__(self, config, reddit):
        super(DailyPinCommand, self).__init__(config, reddit)
        self.command_text = "!dailypin"

    def leave_comment_reply(self, comment, reply):
        database.set_processed_content(comment.fullname, Path(__file__).stem)
        comment.reply(reply)

    def process_comment(self, comment):
        self.logger.info(f"process dailypin command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        user = comment.author.name

        # ensure the author is a moderator or automoderator
        can_use_command = 0
        if user.lower() == "automoderator" or user.lower() == "ethtradercommunity":
            can_use_command = 1
        else:
            dist_round = database.get_distribution_round()[0]
            result = json.load(urllib.request.urlopen(f'https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/moderators/moderators_{dist_round}.json'))
            mods = [m['name'] for m in result]

            if user in mods:
                can_use_command = 1

        if not can_use_command:
            self.leave_comment_reply(comment, f'Sorry u/{user}, this command is only for moderators.')
            return

        was_success = 0
        for count in range(0, 5):
            if database.set_daily_pin(comment.submission.fullname, comment.fullname):
                was_success = 1
                break

            # the post-meta has not been created for this daily yet, give post-bot some time to create it
            time.sleep(4)

        if was_success:
            self.leave_comment_reply(comment, f'Comment successfully registered as the daily pin.')
        else:
            self.leave_comment_reply(comment, f'An error occured while trying to register the daily pin. Please try again.')
