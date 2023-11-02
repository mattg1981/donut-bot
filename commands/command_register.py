from web3 import Web3

from commands import shared, database
from commands.command import Command
import re


class RegisterCommand(Command):
    VERSION = 'v0.1.20231030-reg'
    COMMENT_SIGNATURE = f'\n\n^(donut-bot {VERSION})'

    def __init__(self, config):
        super(RegisterCommand, self).__init__(config)
        self.command_text = "!register"

    def leave_comment_reply(self, comment, reply):
        reply += self.COMMENT_SIGNATURE
        comment.reply(reply)
        database.set_processed_content(comment.fullname)

    def process_command(self, comment):
        if comment.author.name.lower() == shared.Me:
            return

        self.logger.info(f"process reg command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname) is not None:
            self.logger.info("  previously processed...")
            return

        user = comment.author.name

        # handle `!register status` command
        if f'{self.command_text} status' in comment.body.lower():
            self.logger.info("  checking status")
            result = database.get_user_by_name(user)

            if result is None or len(result) == 0:
                self.logger.info("    not registered")
                self.leave_comment_reply(comment,
                                         f'u/{user} is not registered.  Please use the `{self.command_text} <address'
                                         f'>` command to register your wallet address.')
            else:
                self.logger.info("    registered")
                self.leave_comment_reply(comment,
                                         f'u/{user} is registered with the following address: `{result["address"]}`')
            return

        # handle `!register <address>` command
        p = re.compile(f'{self.command_text}\\s+(0x[a-fA-F0-9]{{40}})\\b')
        re_result = p.match(comment.body)
        if re_result:
            address = re_result.group(1)

            self.logger.info("  checking address uniqueness")
            address_exists = database.get_user_by_address(address)
            if address_exists is None:

                self.logger.info(f"  attempting to register {user} with wallet ...{address[len(address) - 5:]}")

                result = database.insert_or_update_address(user, address, comment.fullname)

                if result:
                    self.logger.info("  success...")
                    self.leave_comment_reply(comment,
                                             f'u/{user} successfully registered with the following address: `{address}`')
                else:
                    self.logger.info("  unable to register wallet at this time.")
                    self.leave_comment_reply(comment, f'Unable to register at this time.  Please try again later.')
                return
            else:
                self.logger.warning("  address exists")

                if address_exists["username"].lower() == comment.author.name.lower():
                    self.leave_comment_reply(comment,
                                             f'u/{comment.author.name} is already registered with that address.')
                else:
                    self.leave_comment_reply(comment,
                                             f'Sorry u/{comment.author.name}, someone has already registered with that address.')
                return

        # handle `!register <ENS address>` command
        p = re.compile(f'{self.command_text}\\s+([\\w+.-]+.eth)')
        re_result = p.match(comment.body)
        if re_result:
            self.logger.info("  ENS address")
            ens_address = re_result.group(1)

            self.logger.info("  checking address uniqueness")
            address_exists = database.get_user_by_address(ens_address)
            if address_exists is not None:
                self.logger.warning("  address exists")

                if address_exists["username"].lower() == comment.author.name.lower():
                    self.leave_comment_reply(comment, f'u/{user} is already registered with that address.')
                else:
                    self.leave_comment_reply(comment, f'Sorry u/{user}, someone has already registered with that '
                                                      f'address.')
                return

            try:
                self.logger.info("  attempting to resolve ENS...")
                # todo parameterize this call
                w3 = Web3(Web3.HTTPProvider('https://ethereum.publicnode.com'))
                if w3.is_connected():
                    self.logger.info("  connected to public node...")
                    # check to verify the ENS address resolves
                    eth_address = w3.ens.address(ens_address)

                    if eth_address is None:
                        self.logger.warn("  ENS did not resolve...")
                        self.leave_comment_reply(comment,
                                                 f'The ENS name specified `{ens_address}` does not currently resolve '
                                                 f'to an address. Unable to register ENS address at this time.  '
                                                 f'Please ensure you typed the correct address or try again later.')
                        return

                    result = database.insert_or_update_address(user, ens_address, comment.fullname)

                    if result:
                        self.logger.info("  success...")
                        self.leave_comment_reply(comment, f'u/{user} successfully registered with `{ens_address}`')
                    else:
                        self.logger.warn("  unable to register wallet at this time.")
                        self.leave_comment_reply(comment, f'Unable to register ENS address at this time.  Please '
                                                          f'ensure you typed the correct address or try again later.')

                    return

            except Exception as e:
                self.logger.error(e)
                self.leave_comment_reply(comment, f'Unable to register ENS address at this time.  Please ensure'
                                                  f' you typed the correct address or try again later.')
                return

        self.logger.warn(f"  invalid address format or no address was supplied")
        self.leave_comment_reply(comment, f"Invalid address.  Please ensure the address is in the format '0x' "
                                              f"followed by 40 hexadecimal characters or a valid ENS address.")
