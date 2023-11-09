import re
from unittest import TestCase

from commands.command_tip import TipCommand


class TestTipCommand(TestCase):
    def test_can_handle(self):
        tip = TipCommand("config")
        if not tip.can_handle("!tip"):
            self.fail()

        if not tip.can_handle("!tip "):
            self.fail()

        comment = "'I am so sorry bro, I did not notice it.\n\n!tip 10'"

        print(comment)
        print(repr(comment))
        # comment = comment.replace("\r", "")
        # comment = comment.replace("\n", "")

        if "!tip" in comment:
            pass

        if not tip.can_handle(comment):
            self.fail()

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