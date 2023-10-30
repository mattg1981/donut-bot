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
        # base_dir = os.path.dirname(os.path.abspath(__file__))
        # config_path = os.path.join(base_dir, "../config.json")
        # with open(os.path.normpath(config_path), 'r') as f:
        #     self.config = json.load(f)
        self.config = config

    def can_handle(self, comment):
        return self.command_text.lower() in comment.body.lower()

    def get_db_path(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "../database/donut-bot.db")
        return os.path.normpath(db_path)

    @abc.abstractmethod
    def process_command(self, comment):
        """Method documentation"""
        return
