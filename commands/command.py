import abc
import logging
import re
from pathlib import Path

from praw.models import Comment

from config import Community, CommunityFeatures
from database import database


class Command:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        self.logger = logging.getLogger("donut_bot")
        self.command_text = ''

    def can_handle(self, comment: Comment):
        if isinstance(self.command_text, str):
            p = re.compile(f'{self.command_text.lower()}($|\\s)')
            return p.search(comment.lower())

        elif isinstance(self.command_text, list):
            for cmd in self.command_text:
                cmd = cmd.replace('[', '\[').replace(']', '\]')
                p = re.compile(f'{cmd.lower()}($|\\s)')
                if p.search(comment.lower().replace('\\[', '[').replace('\\]', ']')):
                    return True

        return False

    def process(self, comment: Comment, community_config: Community) -> None:
        try:
            self.logger.info(
                f"processing -> {{ content_id: '{comment.fullname}', author: '{comment.author.name}', url: 'https://reddit.com/comments/{comment.submission.id}/_/{comment.id}' }}")

            if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
                self.logger.info("{{ previously_processed: true }}")
                return

            author = comment.author.name
            community = comment.subreddit.display_name.lower()

            if not self.is_community_feature_enabled(community_config.features):
                self.process_comment(comment, author, community_config)

            database.set_processed_content(comment.fullname, Path(__file__).stem)
        except Exception as e:
            self.logger.error(e)

    @abc.abstractmethod
    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        """Each concrete implementation of Command needs to override this method"""
        pass

    @abc.abstractmethod
    def process_comment(self, comment: Comment, author: str, community: Community) -> None:
        """Each concrete implementation of Command needs to override this method"""
        pass
