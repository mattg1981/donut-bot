from praw.models import Comment

from cache import cache
from commands import Command
from config import Community, CommunityFeatures
from database import database
from reddit.reddit_api import RedditAPI


class FlairCommand(Command):
    def __init__(self):
        super(FlairCommand, self).__init__()
        self.command_text = "!flair"

    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        return features.flair

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:

        # handle the command not starting with `!flair`
        if not comment.body.lower().startswith(self.command_text):
            comment.reply(f"Sorry u/{author}, the command should start with `!flair` and then immediately be followed "
                          f"by the flair you would like to set.")
            return

        if not cache.is_special_member(author, community.name):
            comment.reply(f"Sorry u/{author}, this command can only be used by users with a special membership.\n\n"
                          f"[Click here](https://donut-dashboard.com/#/membership) to learn more or to purchase a membership!")
            return

        # handle reset command
        if comment.body.lower().strip() == f"{self.command_text} reset":
            database.reset_custom_flair(author)
            comment.reply("Successfully reset custom flair.")
            return

        # otherwise handle changing the flair text
        new_flair = f':sm: {comment.body.replace(self.command_text, "").strip()}'

        RedditAPI().instance.subreddit(comment.subreddit.display_name).flair.set(author, text=new_flair,
                                                                                 flair_template_id="da1b88dc-8e17-11ee-8d85-86deef0eb333")

        database.set_custom_flair(author, community.name, new_flair)
        comment.reply("Successfully set custom flair.")
