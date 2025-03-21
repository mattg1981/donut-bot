from unittest import TestCase

from models.offchaintip import OffchainTip


class TestOfChainTips(TestCase):

    def test_toStr(self):
        tip = OffchainTip("Next_Statement6145", "Odd-Radio-8500", 1, 0.0041, "donut", "t1_lbee7kl", "t3_1du5xaq",
                          "1du5xaq", "ethtrader", True, "")
        actual = "[valid]: True [sender]: Next_Statement6145 [recipient]: Odd-Radio-8500 [amount]: 1 [token]: donut"
        self.assertEqual(tip.__str__(), actual)
