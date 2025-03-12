import abc
import logging
import re
from pathlib import Path

# spell-checker: disable
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
            self.logger.info(f"processing -> "
                             f"content_id: '{comment.fullname}', "
                             f"author: '{comment.author.name}', "
                             f"url: 'https://reddit.com/comments/{comment.submission.id}/_/{comment.id}' ")

            if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
                self.logger.info("\tpreviously_processed: true")
                return

            author = comment.author.name

            if not self.is_community_feature_enabled(community_config.features):
                self.process_comment(comment, author, community_config)

            database.set_processed_content(comment.fullname, Path(__file__).stem)
        except Exception as e:
            self.logger.error(e)

    @abc.abstractmethod
    def is_community_feature_enabled(self, features: CommunityFeatures) -> bool:
        """
        Method to check if a command is enabled for a specific community.
        
        
        **This is an abstract method which must be implemented by concrete classes.**

        Args:
            features (CommunityFeatures): The CommunityFeatures object for the community

        Returns:
            bool: True if this command is enabled for the community, False otherwise
        """
        pass

    @abc.abstractmethod
    def process_comment(self, comment: Comment, author: str, community: Community) -> None:
        """        
        This method is called when a comment is found that contains the  
        the `command_text` property and `is_community_feature_enabled()` returns true for this command.
        
        **This is an abstract method which must be implemented by concrete classes.**

        Args:
            comment (Comment): The comment returned by the Reddit API
            author (str): The author of this comment
            community (Community): The Community that this comment was posted in
        """
        pass
