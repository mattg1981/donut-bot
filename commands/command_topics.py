import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from praw.models import Comment

from commands import Command
from config import Community
from database import database


class TopicCommand(Command):
    def __init__(self, config, reddit):
        super(TopicCommand, self).__init__(config, reddit)
        self.command_text = "!topics"
        self.topics = {}

    def leave_comment_reply(self, comment, reply):
        database.set_processed_content(comment.fullname, Path(__file__).stem)
        comment.reply(reply)

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:
        self.logger.info(f"process post command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        community = comment.subreddit.display_name.lower()

        if "last_update" not in self.topics or datetime.now() - timedelta(minutes=5) >= \
                self.topics["last_update"]:
            self.topics['last_update'] = datetime.now()
            self.topics['limits'] = (json.load(urllib.request.urlopen("https://raw.githubusercontent.com/EthTrader/"
                                                                      "topic-limiting/main/topic_limits.json")))

        at_or_above_limit = [t for t in self.topics['limits']['data'] if t['current'] >= t['limit']
                             and t['community'] == community]

        if len(at_or_above_limit) > 0:
            reply = "The following topics are currently at or over the limit:\n\n"
            for topic in at_or_above_limit:
                reply += f"- {topic['display_name']} ({topic['current']} / {topic['limit']})\n"
        else:
            reply = "No topics are currently being limited."

        reply += "\n\n[Click here](https://www.reddit.com/r/ethtrader/comments/1fyb8rv/rethtrader_automated_topic_limiter_topics_allowed/) for more information on topic limits.  Additionally, you can view the full list [here](https://donut-dashboard.com/#/topiclimits)."

        self.leave_comment_reply(comment, reply)
