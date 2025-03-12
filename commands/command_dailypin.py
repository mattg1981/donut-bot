import time

from praw.models import Comment

from cache import cache
from commands import Command
from config import Community, CommunityFeatures
from database import database


class DailyPinCommand(Command):

    def __init__(self):
        super(DailyPinCommand, self).__init__()
        self.command_text = "!dailypin"

    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        return features.daily_pin

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:

        # as of this writing, the community.ignore property is a good list of users (outside the mod team)
        # that can use this command.  If this scenario changes, it would be wise to add config elements at a community
        # level to determine who can use this command

        # community_config = next((c for c in Config().communities if c.name.lower() == community.name), None)

        if not author in community.ignore and not cache.is_moderator(author, community.name):
            comment.reply(f'Sorry u/{author}, this command is only for moderators.')
            return

        # there exists the potential for a race condition where the post-bot may not have processed this post
        # yet.  If so, we will not be able to set_daily_pin() on it yet. So we check to see if the post exists
        # in our metadata/database yet, and if not, sleep for some period of time and try again.
        for count in range(max := 5):
            if database.get_post(comment.submission.fullname):
                break

            if count + 1 != max:
                time.sleep(10)

        if database.set_daily_pin(comment.submission.fullname, comment.fullname):
            comment.reply('Comment successfully registered as the daily pin.')
        else:
            comment.reply('An error occurred while trying to register the daily pin. Please try again.')
