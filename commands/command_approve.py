import html

from praw.models import Comment

from cache import cache
from commands import Command
from config import Config, Community, CommunityFeatures


class ApproveCommand(Command):
    def __init__(self):
        super(ApproveCommand, self).__init__()
        self.command_text = ["!approve", "[AutoModApprove]"]

    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        return features.post_approve

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:
        # ensure this comment is a top level comment on a post
        if not comment.parent_id == comment.submission.fullname:
            comment.reply(f"Sorry u/{author}, you can only use this command to approve posts.")
            return

        # ensure the post is in fact removed
        if not comment.submission.removed_by_category:
            comment.reply(f"Sorry u/{author}, this post does not appear to be removed/hidden.")
            return

        # ensure the post was not removed by a moderator
        if comment.submission.removed_by_category and comment.submission.removed_by_category.lower() == "moderator":
            subject = 'Petition to Approve Post'
            url = f'https://reddit.com/comments/{comment.submission.id}'
            message = f'The following post was removed by a moderator but I am petitioning to have it restored: {url}'

            modmail = (f"[modmail](https://www.reddit.com/message/compose?to=/r/{community}&subject="
                       f"{html.escape(subject)}&message={html.escape(message)})")

            comment.reply(f"Sorry u/{author}, this post was removed by a moderator.  To restore "
                          f"this post, please submit a {modmail} request.")
            return

        # a perk of special memberships is that you can approve posts even if you don't have enough governance weight
        if not cache.is_special_member(author, comment.subreddit.display_name):
            # get user weight
            user_weight = cache.get_user_weight(author)

            config = Config()
            approve_weight = config.posts.approve_weight

            # ensure they have enough weight to use this command
            if user_weight < approve_weight:
                comment.reply(f"Sorry u/{author}, you must have {str(approve_weight)} governance weight to "
                              f"use this command.")
                return

        # all checks passed, approve the post
        comment.submission.mod.approve()
        comment.reply(f"u/{author} has approved this post.")
