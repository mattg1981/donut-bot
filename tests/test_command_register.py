import re
from unittest import TestCase

from web3 import Web3


class TestRegisterCommand(TestCase):

    def test_ens_name(self):
        ens_address = "clarson.eth";
        p = re.compile("([\w+.]+.eth)")
        re_result = p.match(ens_address)
        if re_result:
            address = re_result.group(0)
            w3 = Web3(Web3.HTTPProvider('https://ethereum.publicnode.com'))
            connected = w3.is_connected()
            eth_address = w3.ens.address(address)
            return

        self.fail()

