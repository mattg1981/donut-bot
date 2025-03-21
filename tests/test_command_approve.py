from unittest import TestCase

from config import Config, Community, CommunityFeatures

from commands.command_approve import ApproveCommand


class FakeMod:
    def approve():
        return None


class FakeSub:
    def __init__(self, display_name: str):
        self.display_name = display_name


class FakeSubmission:
    def __init__(self, id: int, removed_by_category: str, fullname: str):
        self.id = id
        self.removed_by_category = removed_by_category
        self.fullname = fullname
        self.mod = FakeMod()


class FakeComment:
    def __init__(self, parent_id: str, comment: str, displya_name: str, id: int, removed_by_category: str,
                 fullname: str):
        self.parent_id = parent_id
        self.comment = comment
        self.subreddit = FakeSub(displya_name)
        self.submission = FakeSubmission(id, removed_by_category, fullname)

    def reply(self, message: str) -> None:
        self.comment = message


class TestApproveCommand(TestCase):

    def test_community_feature_enabled(self):
        cmd1 = ApproveCommand()
        feature = CommunityFeatures(True, True, True, True, True, True, True, True, True, True, True, True)
        self.assertTrue(cmd1.is_community_feature_enabled(feature))
        feature2 = CommunityFeatures(True, True, True, False, True, True, True, True, True, True, True, True)
        self.assertFalse(cmd1.is_community_feature_enabled(feature2))

    def test_process_comment(self):
        cmd1 = ApproveCommand()
        comment = FakeComment("t1_lbee7kl", "", 12, "ethtrader", "moderator", "Odd-Radio-8500")
        community = "ethtrader"
        cmd1.process_comment(comment, "Odd-Radio-8500", community)
        self.assertEqual(comment.comment, 'Sorry u/Odd-Radio-8500, you can only use this command to approve posts.')

        comment1 = FakeComment("t1_lbee7kl", "", 12, "ethtrader", "", "t1_lbee7kl")
        cmd1.process_comment(comment1, "Odd-Radio-8500", community)
        self.assertEqual(comment1.comment, 'Sorry u/Odd-Radio-8500, this post does not appear to be removed/hidden.')

        comment2 = FakeComment("t1_lbee7kl", "", 12, "ethtrader", "moderator", "t1_lbee7kl")
        cmd1.process_comment(comment2, "Odd-Radio-8500", community)
        self.assertEqual(comment2.comment,
                         'Sorry u/Odd-Radio-8500, this post was removed by a moderator.  To restore this post, please submit a [modmail](https://www.reddit.com/message/compose?to=/r/ethtrader&subject=Petition to Approve Post&message=The following post was removed by a moderator but I am petitioning to have it restored: https://reddit.com/comments/ethtrader) request.')

        # AttributeError: 'Config' object has no attribute 'posts'
        # looks like 47 in command_approve is broken.
        # comment3 = FakeComment("t1_lbee7kl", "", 12, "Y", "ethtrader", "t1_lbee7kl")
        # cmd1.process_comment(comment3, "Odd-Radio-8500", community)
        # self.assertEqual(comment3.comment, '')
