from commands import shared, database
from commands.command import Command
import re


class RegisterCommand(Command):

    VERSION = 'v0.1.20231030-reg'
    COMMENT_SIGNATURE = f'\n\n^(This output was generated by donut-bot {VERSION})'

    def __init__(self, config):
        super(RegisterCommand, self).__init__(config)
        self.command_text = "!register"

    def process_command(self, comment):
        if comment.author.name.lower() == shared.Me:
            return

        self.logger.info(f"process reg command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname) is not None:
            self.logger.info("  previously processed...")
            return

        # if comment.saved:
        #     self.logger.info("  previously processed...")
        #     return

        user = comment.author.name

        # handle `!register status` command
        if f'{self.command_text} status' in comment.body.lower():
            self.logger.info("  checking status")
            result = database.get_address_for_user(user)

            if result is None or len(result) == 0:
                self.logger.info("    not registered")
                reply_comment = (f'u/{user} is not registered.  Please use the `{self.command_text} <address>` command '
                                 f'to register your wallet address.')
            else:
                self.logger.info("    registered")
                reply_comment = f'u/{user} is registered with the following address: `{result["address"]}`'

        else:
            # handle `!register <address>` command
            p = re.compile(f'{self.command_text}\\s+(0x[a-fA-F0-9]{{40}})\\b')
            re_result = p.match(comment.body)
            if re_result:
                address = re_result.group(1)

                self.logger.info(f"  attempting to register {user} with wallet ...{address[len(address) - 5:]}")

                result = database.insert_or_update_address(user, address, comment.fullname)

                if result:
                    self.logger.error("  success...")
                    reply_comment = f'u/{user} successfully registered with the following address: `{address}`'
                else:
                    self.logger.error("  unable to register wallet at this time.")
                    reply_comment = f'Unable to register at this time.  Please try again later.'
            else:
                self.logger.warn(f"  invalid address or not address was supplied")
                reply_comment = (f"Invalid address.  Please ensure the address is in the format '0x' followed by 40 "
                                 f"hexadecimal characters")

        reply_comment += self.COMMENT_SIGNATURE
        comment.reply(reply_comment)
        # comment.save()
        database.set_processed_content(comment.fullname)
