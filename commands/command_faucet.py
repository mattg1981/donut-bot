import json
import os
import time
from decimal import Decimal

from web3 import Web3
from web3.gas_strategies.time_based import medium_gas_price_strategy

from database import database as db
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from commands.command import Command


class FaucetCommand(Command):
    VERSION = 'v0.1.20231130-faucet'
    COMMENT_SIGNATURE = f'\n\n^(donut-bot {VERSION})'

    def __init__(self, config):
        super(FaucetCommand, self).__init__(config)

        self.command_text = "!faucet"

        with open(os.path.normpath("contracts/contrib_gnosis_abi.json"), 'r') as f:
            self.contrib_abi = json.load(f)

        # todo: move to config file
        self.contrib_address = "0xFc24F552fa4f7809a32Ce6EE07C09Dcd7A41988F"

    def leave_comment_reply(self, comment, reply):
        reply += f"\n\n💥 Please help support this faucet by sending xDai (on the Gnosis chain) to:\n`{self.config['faucet_wallet_address']}`."
        reply += self.COMMENT_SIGNATURE

        db.set_processed_content(comment.fullname)
        comment.reply(reply)

    def process_comment(self, comment):
        self.logger.info(f"process faucet command - content_id: {comment.fullname} | author: {comment.author.name}")

        if db.has_processed_content(comment.fullname) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        user = comment.author.name

        # ensure the user is registered
        registered_user = db.get_user_by_name(user)
        if not registered_user:
            self.logger.info("  user not registered")
            self.leave_comment_reply(comment,
                                     f"❌ Sorry u/{user}, you need to be [registered]({self.config['e2t_post']}) to use this command!")
            return

        faucet_eligible = db.get_faucet_eligible(user)
        if not faucet_eligible:
            self.logger.info("  user dripped in last 28 days...")
            self.leave_comment_reply(comment, f"❌ Sorry u/{user}, you can only use the faucet once every 28 days!")
            return

        for i in range(1, 8):
            try:
                self.logger.info(f"  connect to ankr rpc service ... attempt {i}")
                w3 = Web3(Web3.HTTPProvider(os.getenv('ANKR_API_PROVIDER')))
                if w3.is_connected():
                    self.logger.info("  connected to ankr")
                else:
                    self.logger.warning("  failed to connect, attempting to retry...")
                    continue

                user_address = registered_user['address']
                if user_address.islower() and '.eth' not in user_address:
                    user_address = Web3.to_checksum_address(user_address)

                # connected, now find contrib for user
                contrib_contract = w3.eth.contract(address=w3.to_checksum_address(self.contrib_address),
                                                   abi=self.contrib_abi)
                contrib_token_balance = contrib_contract.functions.balanceOf(
                    w3.to_checksum_address(user_address)).call()
                contrib_balance = Decimal(contrib_token_balance) / Decimal(10 ** 18)

                if contrib_balance < 50:
                    self.logger.warning(f"  not enough contrib.  contrib_balance: [{contrib_balance}]")
                    self.leave_comment_reply(comment,
                                             f"❌ Sorry u/{user}, you must earn 50 contrib before using the faucet.")
                    return

                balance = w3.from_wei(w3.eth.get_balance(w3.to_checksum_address(self.config['faucet_wallet_address'])), "ether")

                if balance < 0.01:
                    self.logger.warning(f"  faucet is dry.  balance: [{balance}]")
                    self.leave_comment_reply(comment, f"❌ Sorry u/{user}, the faucet is dry")
                    return

                drip_amount = .0025

                # all checks passed, we are good to drip
                # w3.eth.set_gas_price_strategy(medium_gas_price_strategy)
                w3.eth.set_gas_price_strategy(rpc_gas_price_strategy)
                tx = {
                    'chainId': 100,
                    'from': w3.to_checksum_address(self.config['faucet_wallet_address']),
                    'to': user_address,
                    'value': w3.to_wei(drip_amount, 'ether'),
                    'nonce': w3.eth.get_transaction_count(w3.to_checksum_address(self.config['faucet_wallet_address'])),
                    'gasPrice': w3.eth.generate_gas_price(),
                    'gas': 21000
                }

                # sign the transaction
                signed = w3.eth.account.sign_transaction(tx, os.getenv('FAUCET_WALLET_PRIVATE_KEY'))

                # send the transaction
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                human_readable_tx_hash = w3.to_hex(tx_hash)
                self.logger.info(f"  success!  tx_hash: [{human_readable_tx_hash}]")

                db_insert = db.add_faucet_history(user, user_address, 'OUTBOUND', drip_amount,
                                                  human_readable_tx_hash, receipt['blockNumber'])
                if not db_insert:
                    self.logger.error("  failed to write history to faucet")

                self.leave_comment_reply(comment,
                                         f"💧 u/{user} was [SENT](https://gnosisscan.io/tx/{human_readable_tx_hash}) {drip_amount} xDai")
                return
            except Exception as e:
                self.logger.error(f"  {e}")
                time.sleep(1)

        self.leave_comment_reply(comment, "❌ Something went wrong, please try again later.")
        # return