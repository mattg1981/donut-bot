import json
import urllib.request

from datetime import datetime, timedelta
from pathlib import Path
from database import database
from commands.command import Command


class FlairCommand(Command):
    def __init__(self, config, reddit):
        super(FlairCommand, self).__init__(config, reddit)
        self.command_text = "!flair"
        self.special_membership = {}

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

        if "last_update" not in self.special_membership or datetime.now() - timedelta(minutes=12) >= \
                self.special_membership["last_update"]:
            self.special_membership['last_update'] = datetime.now()
            self.special_membership['members'] = (
                json.load(urllib.request.urlopen(self.config["membership"]["members"])))

        # handle the command not starting with `!flair`
        if not comment.body.lower().startswith(self.command_text):
            self.leave_comment_reply(comment, "Improper use of command.  Command should start with `!flair` and "
                                              "then immediately followed by the flair you would like to set.")
            return

        community = comment.subreddit.display_name.lower()
        special_member = next((m for m in self.special_membership['members'] if m['redditor'].lower() == user.lower()
                               and (m['community'].lower() == community or m['community'] == 'all')), None)

        if not special_member:
            self.leave_comment_reply(comment, f"Sorry u/{user}, "
                                              f"this command can only be used by users with a special membership.")
            return

        # handle reset command
        if comment.body.lower().strip() == f"{self.command_text} reset":
            database.reset_custom_flair(user)
            self.leave_comment_reply(comment, "Successfully reset custom flair.")
            return

        # otherwise handle changing the flair text
        new_flair = f':sm: {comment.body.replace(self.command_text, "").strip()}'

        self.logger.info(f"  setting flair to [{new_flair}]")

        self.reddit.subreddit(comment.subreddit.display_name).flair.set(user,
                                                                        text=new_flair,
                                                                        flair_template_id ="da1b88dc-8e17-11ee-8d85-86deef0eb333")

        # todo save the subreddit so that a user can have different flairs in different subreddits
        # todo note: will need to update sqlite schema for flair table

        database.set_custom_flair(user, new_flair)
        self.leave_comment_reply(comment, "Successfully set custom flair.")
