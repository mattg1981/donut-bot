from datetime import datetime

from praw.models import Comment

from commands import Command
from config import CommunityFeatures, Community
from database import database


class PostCommand(Command):
    def __init__(self):
        super(PostCommand, self).__init__()
        self.command_text = "!post"

    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        return features.post_command

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:

        cooldown_check = database.get_post_cooldown(author, community.name, community.posts.post_cooldown_in_minutes)
        post_per_day_check = database.get_post_status(author)

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
            comment.reply(f'**Status**: u/{author} is not currently eligible to post.'
                          f'\n\n**Current Time**: `{cooldown_check["now"]} UTC`'
                          f'\n\n**Eligible to Post**: `{next_post_time} UTC`')
            return

        count_result = database.get_post_count_in_last_24h(author, community.name)
        comment.reply(f'**Status**: u/{author} is eligible to post. ('
                      f'{community.posts.max_per_24_hours - int(count_result["count"])} /'
                      f' {community.posts.max_per_24_hours} remaining)')
