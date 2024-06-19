from pathlib import Path
from cache import cache
from database import database
from commands.command import Command


class ApproveCommand(Command):
    VERSION = 'v0.1.20240603-approve'
    COMMENT_SIGNATURE = f'\n\n^(donut-bot {VERSION})'

    def __init__(self, config, reddit):
        super(ApproveCommand, self).__init__(config, reddit)
        self.command_text = ["!approve", "[AutoModApprove]"]

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

        # ensure this comment is a top level comment on a post
        if not comment.parent_id == comment.submission.fullname:
            self.leave_comment_reply(comment, f"Sorry u/{user}, you can only use this command to approve posts.")
            return

        # ensure the post is in fact removed
        if not comment.submission.removed_by_category:
            self.leave_comment_reply(comment, f"Sorry u/{user}, this post does not appear to be removed/hidden.")
            return

        # ensure the post was not removed by a moderator
        if comment.submission.removed_by_category and comment.submission.removed_by_category.lower() == "moderator":
            self.leave_comment_reply(comment, f"Sorry u/{user}, this post was removed by a moderator.  To restore "
                                              f"this post, please submit a modmail request.")
            return

        # ensure a person cannot approve their own post
        # if comment.author.name == comment.submission.author.name:
        #     self.leave_comment_reply(comment, f"Sorry u/{user}, you cannot approve your own submission.")
        #     return

        # get user weight
        weight = cache.get_user_weight(user)

        # ensure they have enough weight to use this command
        if weight < self.config['posts']['approve_weight']:
            self.leave_comment_reply(comment,f"Sorry u/{user}, you must have "
                                     f"{str(self.config['posts']['approve_weight'])} governance weight to "
                                     f"use this command.")
            return

        # all checks passed, approve the post
        comment.submission.mod.approve()
        self.leave_comment_reply(comment, f"u/{user} has approved this post.")
