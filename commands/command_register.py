import os
import re

from praw.models import Comment
from web3 import Web3

from commands import Command
from config import Community
from database import database


class RegisterCommand(Command):
    def __init__(self):
        super(RegisterCommand, self).__init__()
        self.command_text = "!register"

        self.register_address_regex = re.compile(f'{self.command_text}\\s+<*(0x[a-fA-F0-9]{{40}})>*')
        self.register_ens_regex = re.compile(f'{self.command_text}\\s+<*([\\w+.-]+.eth)>*')

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:

        # handle `!register status` command
        if f'{self.command_text} status' in comment.body.lower():
            self.logger.info("  checking status")
            result = database.get_user_by_name(author)

            if result is None or len(result) == 0 or not result["address"]:
                self.logger.info("  not registered")
                link = '[Please see this post for instructions on how to register]()'
                comment.reply(f'u/{author} is not registered.  {link}')
            else:
                self.logger.info("  registered")
                comment.reply(f'u/{author} is registered with the following address: `{result["address"]}`')
            return

        # handle `!register <address>` command
        re_result = self.register_address_regex.search(comment.body)
        if re_result:
            address = re_result.group(1)

            self.logger.info("  checking address uniqueness")
            address_exists = database.get_user_by_address(address)
            if address_exists is None:

                self.logger.info(f"  attempting to register {author} with wallet ...{address[len(address) - 5:]}")

                result = database.insert_or_update_address(author, address, comment.fullname)

                if result:
                    self.logger.info("  success...")
                    comment.reply(f'u/{author} successfully registered with the following address: `{address}`')
                else:
                    self.logger.info("  unable to register wallet at this time.")
                    comment.reply(f'Unable tocomment.reply( register at this time.  Please try again later.')
                return
            else:
                self.logger.warning("  address exists")

                if address_exists["username"].lower() == comment.author.name.lower():
                    comment.reply(f'u/{comment.author.name} is already registered with that address.')
                else:
                    comment.reply(f'Sorry u/{comment.author.name}, someone has already registered with that address.')
                return

        # handle `!register <ENS address>` command
        re_result = self.register_ens_regex.search(comment.body)
        if re_result:
            self.logger.info("  ENS address")
            ens_address = re_result.group(1)

            self.logger.info("  checking address uniqueness")
            address_exists = database.get_user_by_address(ens_address)
            if address_exists is not None:
                self.logger.warning("  address exists")

                if address_exists["username"].lower() == comment.author.name.lower():
                    comment.reply(f'u/{author} is already registered with that address.')
                else:
                    comment.reply(f'Sorry u/{author}, someone has already registered with that address.')
                return

            self.logger.info("  attempting to resolve ENS...")

            try:
                w3 = Web3(Web3.HTTPProvider(os.getenv('INFURA_ETH_PROVIDER')))
                if w3.is_connected():
                    self.logger.info("  connected to INFURA_ETH_PROVIDER...")

                    # check to verify the ENS address resolves
                    eth_address = w3.ens.address(ens_address)

                    if eth_address is None:
                        self.logger.warn("  ENS did not resolve...")
                        comment.reply(f'The ENS name specified `{ens_address}` does not currently resolve to an '
                                      f'address. Unable to register ENS address at this time.  Please ensure you '
                                      f'typed the correct address or try again later.')
                        return

                    result = database.insert_or_update_address(author, ens_address, comment.fullname)

                    if result:
                        self.logger.info("  success...")
                        comment.reply(f'u/{author} successfully registered with `{ens_address}`')
                    else:
                        self.logger.warn("  unable to register wallet at this time.")
                        comment.reply(f'Unable to register ENS address at this time.  Please '
                                                          f'ensure you typed the correct address or try again later.')

                    return

                comment.reply(f'Unable to register ENS address at this time. Please try again later.')
                return
            except Exception as e:
                self.logger.error(e)

        self.logger.warn(f"  invalid address format or no address was supplied")
        comment.reply(f"Invalid address.  Please ensure the address is in the format '0x' "
                                              f"followed by 40 hexadecimal characters or a valid ENS address.")
