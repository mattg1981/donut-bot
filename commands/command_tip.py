import re

from commands import shared, database
from commands.command import Command
from commands.command_register import RegisterCommand


class TipCommand(Command):
    VERSION = 'v0.1.20231030-tip'
    COMMENT_TEST_TX = (f'\n\n^(THIS IS A TEST TRANSACTION)')
    COMMENT_SIGNATURE = f'\n\n^(donut-bot {VERSION} | Learn more about [Earn2Tip](https://www.reddit.com/r/EthTrader_Test/comments/17l2imp/introducing_earn2tip_and_the_new_tipping_bot/?utm_source=share&utm_medium=web2x&context=3))'

    def __init__(self, config):
        super(TipCommand, self).__init__(config)
        self.command_text = "!tip"

    def normalize_amount(self, amount):
        """
        Checks the amount to make sure it is a valid input
        :param amount: the amount parsed from the regex
        :return: a float number of the amount, -1 if it is not able to be parsed
        """

        try:
            result = float(amount)
            result = round(float(result), 5)

            int_value = int(float(result))
            if len(str(int_value)) > 10:
                raise Exception("Number too large")

            return result if result > 0 else -1
        except Exception as e:
            self.logger.error(f"invalid amount specified: {amount}")
            self.logger.error(e)
            return -1

    def handle_tip_status(self, comment):
        self.logger.info("  user checking status")
        result = database.get_tip_status_for_current_round(comment.author.name)

        if len(result) == 0:
            self.leave_comment_reply(comment,
                                     f"u/{comment.author.name} has not earn2tipped anyone this round")
            return

        tip_text = f"u/{comment.author.name} has earn2tipped the following this round:\n\n"
        for tip in result:
            amount = round(float(tip["amount"]), 5)
            tip_text += f"&ensp;&ensp;{amount} {tip['token']} ({tip['count']} tip(s) total)\n\n"

        self.leave_comment_reply(comment, tip_text)

    def handle_tip_sub(self, comment):
        self.logger.info("  sub status")
        result = database.get_sub_status_for_current_round(comment.subreddit.display_name)

        if len(result) == 0:
            self.leave_comment_reply(comment,
                                     f"Nobody has earn2tipped in r/{comment.subreddit.display_name} this round")
            return

        # todo pull this logic out into a def
        #  it is repeated in another place and it will also make the code testable
        community_tokens = self.config["community_tokens"]
        for ct in community_tokens:
            if ct["community"].lower() == f"r/{comment.subreddit.display_name.lower()}":
                valid_tokens = ct["tokens"]

        token_reply = f"Valid tokens for r/{comment.subreddit.display_name} are:\n\n"
        for token in valid_tokens:
            token_reply += f"&ensp;&ensp;{token['name']} {' (default)' if token['is_default'] else ''}\n\n"

        tip_text = f"r/{comment.subreddit.display_name} has had the following earn2tip tips this round:\n\n"
        for tip in result:
            amount = round(float(tip["amount"]), 5)
            tip_text += f"&ensp;&ensp;{amount} {tip['token']} ({tip['tip_count']} tips total)\n\n"

        self.leave_comment_reply(comment, tip_text + token_reply)

    def process_earn2tip(self, comment, user_address, parent_address, parent_username, amount, token, content_id,
                         community):
        result = database.process_earn2tip(user_address,
                                           parent_address,
                                           parent_username,
                                           amount,
                                           token,
                                           content_id,
                                           community)

        if not result:
            reply = "Error saving tip to the database.  Please try again later."
        else:
            reply = f"u/{comment.author.name} has tipped u/{parent_username} {amount} {token}"
            if not parent_address:
                reply += f"\n\nNOTE: u/{parent_username} is not currently registered and will not receive the tip until they do so."

        self.leave_comment_reply(comment, reply)

    def leave_comment_reply(self, comment, reply):
        reply += self.COMMENT_TEST_TX
        reply += self.COMMENT_SIGNATURE
        comment.reply(reply)
        database.set_processed_content(comment.fullname)

    def process_command(self, comment):
        if comment.author.name.lower() == shared.Me:
            return

        self.logger.info(f"process tip command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname) is not None:
            self.logger.info("  previously processed...")
            return

        # handle '!tip status' command
        p = re.compile(f'{self.command_text}\\s+status')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.handle_tip_status(comment)
            return

        # handle '!tip sub' command
        p = re.compile(f'{self.command_text}\\s+sub')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.handle_tip_sub(comment)
            return

        parent_author = comment.parent().author.name
        parent_result = None
        user_address = None
        parent_address = None

        self.logger.info(f"getting user addresses for {comment.author.name} and {parent_author}")
        result = database.get_users_by_name([comment.author.name, parent_author])

        for r in result:
            if r["username"].lower() == comment.author.name.lower():
                user_address = r["address"]
            if r["username"].lower() == parent_author.lower():
                parent_result = r
                parent_address = r["address"]

        if not user_address:
            self.logger.info("user not registered")
            reg = RegisterCommand()
            self.leave_comment_reply(comment,
                                     f"Cannot tip u/{parent_author} - you are not registered.  Please use the {reg.command_text} command to register!")
            return

        if not parent_address:
            self.logger.info("  parent is not registered")
            if not parent_result:
                self.logger.info("  parent not in db .. adding")
                parent_result = database.add_unregistered_user(parent_author, comment.fullname)
                if not result:
                    self.logger.info("  failed to add to db")
                    self.leave_comment_reply(comment,
                                             f"Cannot tip u/{parent_author} at this time.  Please try again later.")
                    return

            # self.logger.info("author not registered")
            # self.leave_comment_reply(comment, f"Cannot tip u/{parent_author} - that user is not registered")
            # return

        if user_address == parent_address:
            self.logger.info("attempted self tipping")
            self.leave_comment_reply(comment, f"Sorry u/{comment.author.name}, you cannot tip yourself!")
            return

        # find all the configured tokens for this sub
        self.logger.debug("getting community tokens")
        valid_tokens = {}
        community_tokens = self.config["community_tokens"]
        for ct in community_tokens:
            if ct["community"].lower() == f"r/{comment.subreddit.display_name.lower()}":
                valid_tokens = ct["tokens"]

        # find default token for this sub
        self.logger.debug("getting community default token")
        default_token_meta = {}
        for t in valid_tokens:
            if t["is_default"]:
                default_token_meta = t
                break

        # earn2tip scenarios
        #  !tip
        #  !tip 10 donut
        #  !tip 10donut
        #  "This is a good article and deserves !tip 10"
        #  also handles multi line comments as well

        is_handled = False
        parsed_token = ""
        amount = 0

        #  !tip 10\n\nComment on new line
        #  !tip 10\nSingle return (mobile)
        #  !tip 10\n\nSingle return (mobile)
        p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s*[\r\n]+')
        re_result = p.match(comment.body.lower())
        if re_result:
            amount = re_result.group(1)
            is_handled = True

        if not is_handled:
            #  !tip 10 donut
            #  !tip 10 donut with a comment after the tip
            #  !tip 10 donut/n/nWith new lines after the tip
            p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s+(\\w+)')
            re_result = p.match(comment.body.lower())
            if re_result:
                amount = re_result.group(1)
                parsed_token = re_result.group(2)
                is_handled = True

        if not is_handled:
            #  !tip 10
            p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s*')
            re_result = p.match(comment.body.lower())
            if re_result:
                amount = re_result.group(1)
                is_handled = True

        if is_handled:
            self.logger.info("  earn2tip")
            token_meta = {}

            if not parsed_token:
                self.logger.info("  default token")
                token_meta = default_token_meta
            else:
                for t in valid_tokens:
                    if t["name"].lower() == parsed_token.lower():
                        token_meta = t
                        break

                    # handle plural case.  e.g. 'donuts' was supplied but the token is 'donut'
                    if parsed_token.lower()[-1] == 's':
                        if t["name"].lower() == parsed_token.lower()[:-1]:
                            token_meta = t
                            break

            if not token_meta:
                self.logger.info(f"  not a valid token!")
                self.leave_comment_reply(comment,
                                         f"Sorry u/{comment.author.name}, `{parsed_token}` is not a valid token!")
                return

            self.logger.info(f"  to: {parent_author} - amount: {amount} - token: {token_meta['name']}")
            self.process_earn2tip(comment,
                                  user_address,
                                  parent_address,
                                  parent_result["username"],
                                  amount,
                                  token_meta["name"],
                                  comment.fullname,
                                  comment.subreddit.display_name)
            return

        # just !tip (or some sort of edge case that fell through and will
        # get a default comment)
        self.logger.info("  on-chain tipping (or fallback)")
        content_id = comment.parent().fullname
        desktop_link = f"https://www.donut.finance/tip/?action=tip&contentId={content_id}"

        if content_id[:3] == "t1_":
            desktop_link += f"&recipient={parent_author}&address={parent_address}"

        mobile_link = f"https://metamask.app.link/dapp/{desktop_link}"

        comment_reply = f"**[Leave a tip]** [Desktop]({desktop_link}) | [Mobile (Metamask Only)]({mobile_link})"
        comment_reply += ("\n\n*The mobile link works best if you use the "
                          "System Default Browser in the Reddit Client (Settings > Open Links > Default Browser)*")

        self.leave_comment_reply(comment, comment_reply)
