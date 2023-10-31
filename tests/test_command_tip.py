from unittest import TestCase

from commands.command_tip import TipCommand


class TestTipCommand(TestCase):
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
