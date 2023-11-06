import abc
import json
import os
import logging

class Command:
    __metaclass__ = abc.ABCMeta
    command_text = ''
    logger = logging.getLogger("donut_bot")
    config = {}

    def __init__(self, config):
        self.config = config

    def can_handle(self, comment):
        return f'{self.command_text.lower()} ' in comment.body.lower()

    @abc.abstractmethod
    def process_comment(self, comment):
        """Method documentation"""
        return
