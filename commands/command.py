import abc
import logging
import re


class Command:
    __metaclass__ = abc.ABCMeta
    command_text = ''
    logger = logging.getLogger("donut_bot")
    config = {}

    def __init__(self, config, reddit):
        self.config = config
        self.reddit = reddit

    def can_handle(self, comment):
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

    @abc.abstractmethod
    def process_comment(self, comment):
        """Method documentation"""
        return
