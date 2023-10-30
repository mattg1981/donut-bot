import re

from commands import shared, database
from commands.command import Command


class TipCommand(Command):
    VERSION = 'v0.1.20231030-tip'
    COMMENT_SIGNATURE = f'\n\n^(This output was generated by donut-bot {VERSION})'

    def __init__(self, config):
        super(TipCommand, self).__init__(config)
        self.command_text = "!tip"

    def normalize_amount(self, amount):
        if amount[-1] == '.':
            amount = amount[0:-1]

        int_value = int(float(amount))
        if len(str(int_value).lstrip("0")) > 10:
            raise Exception("Number too large")

        if "." in amount:
            amount = round(float(amount), 5)

        return amount

    def leave_comment_reply(self, comment, reply):
        reply += self.COMMENT_SIGNATURE
        comment.reply(reply)
        comment.save()

    def process_command(self, comment):
        if comment.author.name.lower() == shared.Me:
            return

        self.logger.info(f"process tip command - content_id: {comment.fullname} | author: {comment.author.name}")

        if comment.saved:
            self.logger.info("  previously processed...")
            return

        # handle '!tip status' command
        p = re.compile(f'{self.command_text}\\s+status')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.logger.info("  user checking status")
            result = database.get_tip_status_for_current_round(comment.author.name)

            if len(result) == 0:
                self.leave_comment_reply(comment, f"u/{comment.author.name} has not earn2tipped anyone this round")
                return

            tip_text = f"u/{comment.author.name} has earn2tipped the following this round:\n\n"
            for tip in result:
                amount = round(float(tip["amount"]), 5)
                tip_text += f"&ensp;&ensp;{amount} {tip["token"]} ({tip["count"]} tip(s) total)\n\n"

            self.leave_comment_reply(comment, tip_text)
            return

        parent = comment.parent()
        author = parent.author.name
        user_address = None
        author_address = None

        self.logger.info("getting user addresses")
        result = database.get_addresses_for_users([comment.author.name, author])

        for user in result:
            if user["username"].lower() == comment.author.name.lower():
                user_address = user["address"]
            if user["username"].lower() == author.lower():
                author_address = user["address"]

        if not user_address:
            self.logger.info("user not registered")
            self.leave_comment_reply(comment, f"Cannot tip u/{author} - you are not registered")
            return

        if not author_address:
            self.logger.info("author not registered")
            self.leave_comment_reply(comment, f"Cannot tip u/{author} - that user is not registered")
            return

        # todo uncomment after testing
        if user_address == author_address:
            self.logger.info("attempted self tipping")
            self.leave_comment_reply(comment, f"Sorry u/{comment.author.name}, you cannot tip yourself!")
            return

        self.logger.debug("getting community tokens")
        # find all the configured tokens for this sub
        valid_tokens = {}
        community_tokens = self.config["community_tokens"]
        for ct in community_tokens:
            if ct["community"].lower() == f"r/{comment.subreddit.display_name.lower()}":
                valid_tokens = ct["tokens"]

        self.logger.debug("getting community default token")
        # find default token for this sub
        default_token_meta = {}
        for t in valid_tokens:
            if t["is_default"]:
                default_token_meta = t
                break

        # handles default token
        # !tip 10
        p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s*$')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.logger.info("  default tipping")
            try:
                amount = self.normalize_amount(re_result.group(1))
            except Exception as e:
                self.logger.warn(e)
                self.leave_comment_reply(comment, f"Sorry u/{comment.author.name}, I could not process that number")
                return

            database.process_earn2tip(user_address,
                                      author_address,
                                      amount,
                                      default_token_meta["name"],
                                      comment.fullname,
                                      comment.subreddit.display_name)

            self.logger.info(f"  to: {comment.author.name} - amount: {amount}")
            self.leave_comment_reply(comment,
                                     f"u/{comment.author.name} has tipped u/{parent.author.name} {amount} {default_token_meta["name"]}")
            return

        # handles comments on a new line after default token
        # !tip 10
        # I think this comment deserves ...
        p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s*\n\n')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.logger.info("  default tipping")
            try:
                amount = self.normalize_amount(re_result.group(1))
            except Exception as e:
                self.logger.warn(e)
                self.leave_comment_reply(comment, f"Sorry u/{comment.author.name}, I could not process that number")
                return

            database.process_earn2tip(user_address,
                                      author_address,
                                      amount,
                                      default_token_meta["name"],
                                      comment.fullname,
                                      comment.subreddit.display_name)

            self.logger.info(f"  to: {comment.author.name} - amount: {amount}")
            self.leave_comment_reply(comment,
                                     f"u/{comment.author.name} has tipped u/{parent.author.name} {amount} {default_token_meta["name"]}")
            return

        # otherwise grab the token after the amount
        # !tip 10 donut ....
        p = re.compile(f'{self.command_text}\\s+([0-9]*\\.*[0-9]*)\\s+(\\w+)\\b')
        re_result = p.match(comment.body.lower())
        if re_result:
            self.logger.info("  specify tipping")
            try:
                amount = self.normalize_amount(re_result.group(1))
            except Exception as e:
                self.logger.warn(e)
                self.leave_comment_reply(comment, f"Sorry u/{comment.author.name}, I could not process that number")
                return
            parsed_token = re_result.group(2)

            self.logger.info(f"  to: {comment.author.name} - amount: {amount} - token: {parsed_token}")

            token_meta = {}

            # determine if the specified token is valid in this sub
            for t in valid_tokens:
                if t["name"].lower() == parsed_token.lower():
                    token_meta = t

            if not token_meta:
                self.logger.info(f"  not a valid token!")
                self.leave_comment_reply(comment,
                                         f"Sorry u/{comment.author.name}, {parsed_token} is not a valid token!")
                return

            self.logger.debug(f"  valid token: {token_meta["name"]}")

            database.process_earn2tip(user_address,
                                      author_address,
                                      amount,
                                      token_meta["name"],
                                      comment.fullname,
                                      comment.subreddit.display_name)

            self.leave_comment_reply(comment,
                                     f"u/{comment.author.name} has tipped u/{parent.author.name} {amount} {token_meta["name"]}")
            return

        # just !tip (or some sort of edge case that fell through and will
        # get a default comment)
        content_id = parent.fullname
        desktop_link = f"https://www.donut.finance/tip/?action=tip&contentId={content_id}"

        if content_id[:3] == "t1_":
            desktop_link += f"&recipient={author}&address={author_address}"

        mobile_link = f"https://metamask.app.link/dapp/{desktop_link}"

        comment_reply = f"**[Leave a tip]** [Desktop]({desktop_link}) | [Mobile (Metamask Only)]({mobile_link})"
        comment_reply += ("\n\n*The mobile link works best if you use the "
                          "System Default Browser in the Reddit Client (Settings > Open Links > Default Browser)*")

        self.leave_comment_reply(comment, comment_reply)
