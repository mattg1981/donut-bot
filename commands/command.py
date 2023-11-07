import abc
import logging
import re


class Command:
    __metaclass__ = abc.ABCMeta
    command_text = ''
    logger = logging.getLogger("donut_bot")
    config = {}

    def __init__(self, config):
        self.config = config

    def can_handle(self, comment):
        p = re.compile(f'{self.command_text}($|\\s)')
        return p.search(comment.lower())

    @abc.abstractmethod
    def process_comment(self, comment):
        """Method documentation"""
        return
