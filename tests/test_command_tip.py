import json
import os
import re
from unittest import TestCase

import praw
from dotenv import load_dotenv

from commands.command_tip import TipCommand
from database import database


class TestTipCommand(TestCase):

    class Submission:
        def __init__(self):
            self.id = None

        @property
        def id(self):
            return self._id

        @id.setter
        def id(self, value):
            self._id = value

    class SubReddit:
        def __init__(self):
            self._display_name = None

        @property
        def display_name(self):
            return self._display_name

        @display_name.setter
        def display_name(self, value):
            self._display_name = value

    class Author:
        def __init__(self):
            self.name = None

        @property
        def name(self):
            return self._name

        @name.setter
        def name(self, value):
            self._name = value
    class Comment:
        def __init__(self, parent):
            self._id = None
            self.author = parent or TestTipCommand.Author()
            self.submission = TestTipCommand.Submission()
            self.subreddit = TestTipCommand.SubReddit()
            self._fullname = None
            self._body = None
            self._parent = parent

        @property
        def body(self):
            return self._body

        @property
        def id(self):
            return self._id
        @property
        def fullname(self):
            return self._fullname

        def parent(self):
            return self._parent

        @body.setter
        def body(self, value):
            self._body = value

        @id.setter
        def id(self, value):
            self._id = value
            
        @fullname.setter
        def fullname(self, value):
            self._fullname = value

    def test_something(self):
        # load config
        with open(os.path.normpath("../config.json"), 'r') as f:
            config = json.load(f)

        command = TipCommand(config)

        parent = TestTipCommand.Comment(None)
        parent.author.name = 'kirtash93'
        parent.fullname = 'parent.fullname'

        comment = TestTipCommand.Comment(parent)
        comment.fullname = 'mock'
        comment.submission.id = 'mock'
        comment.id = 'mock'
        comment.author.name = 'mattg1981'
        comment.body = 'test !Tip 10 !tip u/aminok 10\n\nanother !tip u/odd-radio-8500 30'
        comment.subreddit.display_name = 'ethtrader'

        if command.can_handle(comment.body):
            tips = command.parse_comments_for_tips(comment)
            valid_tips = [t for t in tips if t.is_valid]
            database.process_earn2tips(valid_tips)
            pass
        else:
            self.fail()

    def test_can_handle(self):
        # load environment variables
        load_dotenv()

        with open(os.path.normpath("../config.json"), 'r') as f:
            config = json.load(f)

        tip = TipCommand(config)

        reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                             client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                             username=os.getenv('REDDIT_USERNAME'),
                             password=os.getenv('REDDIT_PASSWORD'),
                             user_agent='automated-test-bot (by u/mattg1981')

        comment = reddit.comment(id='kasy9fi')
        if not tip.can_handle(comment.body):
            self.fail()

        self.assertEqual(True, True)

        comment_body = """Awesome post.

The key is, as you've pointed out, to provide Liquidity in a ranging market.... Such as we have right now ;)

!tip 1"""

        with open(os.path.normpath("../config.json"), 'r') as f:
            config = json.load(f)

        tip = TipCommand(config)

        if not tip.can_handle("!tip"):
            self.fail()

        if not tip.can_handle("!tip "):
            self.fail()

        comment0 = "!tip 20"

        comment1 = "I am so sorry bro, I did not notice it.\n\n!tip 10"

        comment2 = """!tip u/aminok 8 donut
jakdfk
!tip 20
lakdfk
!tip 10 donut !tip 20 donut
!tip 10 !tip 15
!tip u/aminok 15 !tip u/mattg1981 20 donut
aldkflakf
!tip u/am 20
!tip 10"""

        comment3 = """
        I like to onchain tip.
        !tip
        """

        comment4 = """
            !tip 4 donuts
            !tip 3 xdai
        """

        if not tip.can_handle(comment0):
            self.fail()

        tips0 = tip.parse_comments_for_tips(comment0)
        tips1 = tip.parse_comments_for_tips(comment1)
        tips2 = tip.parse_comments_for_tips(comment2)
        tips3 = tip.parse_comments_for_tips(comment3)
        tips4 = tip.parse_comments_for_tips(comment4)

        p = re.compile(f'\\!tip\\s+([0-9]*\\.*[0-9]*)\\s*[\r\n]+')
        re_result = p.search(comment.lower())
        if re_result:
            amount = re_result.group(1)
            pass

        p = re.compile(f'\\!tip\\s+([0-9]*\\.*[0-9]*)\\s+(\\w+)')
        re_result = p.search(comment.lower())
        if re_result:
            amount = re_result.group(1)
            pass

        p2 = re.compile(f'\\!tip\\s+([0-9]*\\.*[0-9]*)\\s*')
        re_result2 = p2.search(comment.lower())
        if re_result2:
            amount = re_result2.group(1)
            pass

        if not tip.can_handle("Let me test\r \n\r \n!tip 1"):
            self.fail()

        if tip.can_handle("!tipExtra"):
            self.fail()

    def test_regex_for_tips(self):
        comment = "!tip 10 donut this is a great comment"

        default_token = False
        parsed_token = ""
        is_handled = False

        p = re.compile('!tip\\s+([0-9]*\\.*[0-9]*)\\s*[\r\n]+')
        re_result = p.search(comment.lower())
        if re_result:
            # default tip and a new line
            amount = re_result.group(1)
            default_token = True
            is_handled = True

        if not is_handled:
            p = re.compile('!tip\\s+([0-9]*\\.*[0-9]*)\\s+(\\w*)[\r\n]+')
            re_result2 = p.search(comment.lower())
            if re_result2:
                amount = re_result2.group(1)
                default_token = False
                parsed_token = re_result2.group(2)
                is_handled = True

        if not is_handled:
            p = re.compile('!tip\\s+([0-9]*\\.*[0-9]*)\\s*([\r\n]*)?(\\w*)(?:[\r\n]*)?')
            re_result3 = p.search(comment.lower())
            if re_result3:
                amount = re_result3.group(1)
                default_token = False
                parsed_token = re_result3.group(2)
                is_handled = True

    def test_normalize_amount(self):
        tip = TipCommand("config")

        amount = "421.68"
        result = tip.normalize_amount(amount)
        self.assertEqual(421.68, result)

        amount1 = "0000025"
        result1 = tip.normalize_amount(amount1)
        self.assertEqual(25, result1)

        amount2 = "421."
        result2 = tip.normalize_amount(amount2)
        self.assertEqual(421, result2)

        amount3 = ".54"
        result3 = tip.normalize_amount(amount3)
        self.assertEqual(.54, result3)

        amount4 = "0.54"
        result4 = tip.normalize_amount(amount4)
        self.assertEqual(.54, result4)

        amount5 = "0.54000005"
        result5 = tip.normalize_amount(amount5)
        self.assertEqual(.54, result5)

        amount6 = "0.540009"
        result6 = tip.normalize_amount(amount6)
        self.assertEqual(.54001, result6)

        amount7 = "10"
        result7 = tip.normalize_amount(amount7)
        self.assertEqual(10, result7)

        amount8 = "1000000000"
        result8 = tip.normalize_amount(amount8)
        self.assertEqual(1000000000, result8)

        amount9 = "9999999999"
        result9 = tip.normalize_amount(amount9)
        self.assertEqual(9999999999, result9)

        amount10 = "9999999999.22222"
        result10 = tip.normalize_amount(amount10)
        self.assertEqual(9999999999.22222, result10)

        amount11 = "99999999999"
        result11 = tip.normalize_amount(amount11)
        self.assertTrue(result11 == -1)

        amount11 = "-420.1"
        result11 = tip.normalize_amount(amount11)
        self.assertTrue(result11 == -1)

        amount12 = "0"
        result12 = tip.normalize_amount(amount12)
        self.assertTrue(result12 == -1)

        amount13 = "0.0"
        result13 = tip.normalize_amount(amount13)
        self.assertTrue(result13 == -1)

        amount14 = "0.01"
        result14 = tip.normalize_amount(amount14)
        self.assertEqual(0.01, result14)
