
from unittest import TestCase

from commands.command_special_membership import SpecialMembershipCommand

class FakeSubReddit:
    def __init__(self, display_name: str):
        self.display_name = display_name

class FakeSubmission:
    def __init__(self, id: str):
        self.id = id
        self.fullname = "FAKE_SUBMISSION"

class FakeAuthor:
    def __init__(self, name: str):
        self.name = name

class FakeComment:
    def __init__(self, parent_id: str, comment: str, author: str, community: str):
        self.reply_message = None
        self.parent_id = parent_id
        self.body = comment
        self.subreddit = FakeSubReddit(community)
        self.author = FakeAuthor(author)
        self.fullname = "FAKE_COMMENT"
        self.id = "FAKE_COMMENT_ID"
        self.submission = FakeSubmission("FAKE_SUBMISSION_ID")

    def reply(self, message: str) -> None:
        self.reply_message = message

class TestSpecialMembershipCommand(TestCase):

    def test_process_comment(self):
        cmd1 = SpecialMembershipCommand(None, None)
        active_member_comment = FakeComment("t1_lbee7kl", "!membership", "mattg1981", "ethtrader")
        cmd1.process_comment(active_member_comment)
        self.assertEqual(active_member_comment.reply_message, 'u/mattg1981, thank you for being a special member in the '
                                                        'ethtrader community! Your current membership is valid until '
                                                        '2025-10-05 15:39:34 UTC.')

        inactive_member_comment = FakeComment("t1_lbee7kl", "!membership", "inactive_user", "ethtrader")
        cmd1.process_comment(inactive_member_comment)
        self.assertEqual(inactive_member_comment.reply_message,
                         'You are not currently a special member in the ethtrader community! [Click here](https://donut-dashboard.com/#/membership) to learn more or to purchase a membership!')

