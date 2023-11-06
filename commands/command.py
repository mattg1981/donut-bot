import abc
import json
import os
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
        p = re.compile(f'{self.command_text}(?:$|\\s)')
        p.match(comment.body.lower())

    @abc.abstractmethod
    def process_comment(self, comment):
        """Method documentation"""
        return
