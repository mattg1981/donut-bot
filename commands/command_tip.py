import json
import os
import re
import urllib.request

from datetime import datetime, timedelta
from pathlib import Path
from database import database
from commands.command import Command
from commands.command_register import RegisterCommand
from models.offchaintip import OffchainTip

USERS = {}


class TipCommand(Command):
    VERSION = 'v0.1.20240111-tip'

    def __init__(self, config, reddit):
        super(TipCommand, self).__init__(config, reddit)
        self.command_text = "!tip"

        delimiters = "\r", "\n"
        newline_pattern = '|'.join(map(re.escape, delimiters))
        self.newline_regex = re.compile(newline_pattern)

        earn2tip_pattern = f"{self.command_text}\s+([uU]\/[A-Za-z0-9_-]+\s+)*([0-9]*\.*[0-9]+)\s*(\w+)*"
        self.earn2tip_regex = re.compile(earn2tip_pattern)

        self.tip_status_regex = re.compile(f'{self.command_text}\\s+status')
        self.tip_sub_regex = re.compile(f'{self.command_text}\\s+sub')

        # find all the configured tokens for this sub
        self.valid_tokens = {}
        self.logger.debug("  getting community tokens")
        community_tokens = self.config["community_tokens"]
        for ct in community_tokens:
            community = ct["community"].lower()
            if community[:2] == "r/":
                community = community[2:]

            self.valid_tokens[community] = ct["tokens"]

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
                raise Exception("  Number too large")

            return result if result > 0 else -1
        except Exception as e:
            self.logger.error(f"  invalid amount specified: {amount}")
            self.logger.error(f'  {e}')
            return -1

    def parse_comments_for_tips(self, comment):
        """
        Parses and returns a list of tips parsed from the passed in comment.
        :param comment: the reddit comment
        :return: a list of tips parsed from the comment
        """
        tips = []

        comment_lines = self.newline_regex.split(comment.body.lower())

        for line in comment_lines:
            search_results = self.earn2tip_regex.findall(line)

            # no match on this line
            if not search_results:
                continue

            for search_result in search_results:
                self.logger.info("  earn2tip detected...")
                recipient = search_result[0]
                amount = search_result[1]
                token = search_result[2]

                is_valid = True
                message = ""

                community = comment.subreddit.display_name.lower()
                sender = comment.author.name

                if recipient:
                    # recipient supplied in the format u/username
                    # so we need to strip the u/ off
                    recipient = recipient[2:].strip()
                else:
                    parent_author = comment.parent().author
                    if not parent_author:
                        self.logger.error(f"  parent_author missing! skipping tip...")
                        continue

                    recipient = parent_author.name

                if not token:
                    default_token = next(x for x in self.valid_tokens[community] if x["is_default"])
                    token = default_token["name"].strip()
                else:
                    # determine if its a valid token
                    token_lookup = next((x for x in self.valid_tokens[community] if x["name"].lower() == token.lower()),
                                        None)

                    # if we did not find the token, lets try to handle plural case.
                    # e.g. 'donuts' was supplied but the token is 'donut'
                    if not token_lookup:
                        if token.lower()[-1] == 's':
                            token = token.lower()[:-1]
                            token_lookup = next(
                                (x for x in self.valid_tokens[community] if x["name"].lower() == token.lower()), None)

                    # we were not able to find the token
                    if not token_lookup:
                        is_valid = False
                        message = f"❌ Sorry u/{sender}, `{token}` is not a valid token for this sub."

                if sender.lower() == recipient.lower():
                    is_valid = False
                    self.logger.info("  attempted self tipping")
                    message = f"❌ Sorry u/{sender}, you cannot tip yourself!"

                if is_valid:
                    normalized_amount = self.normalize_amount(amount)
                    if normalized_amount <= 0:
                        is_valid = False
                        self.logger.error(f"  invalid amount!")
                        self.logger.error(f"  comment body: {repr(comment.body)}")
                        message = f"❌ Sorry u/{sender}, that amount is invalid!"
                    else:
                        amount = normalized_amount

                sender_exists = False
                recipient_exists = False
                if is_valid:
                    result = database.get_users_by_name([sender, recipient])
                    for r in result:
                        if r["username"].lower() == sender.lower():
                            sender_exists = True
                        if r["username"].lower() == recipient.lower():
                            # use the 'official' reddit name, not what was typed in
                            recipient = r["username"]
                            recipient_exists = True

                    if not sender_exists:
                        is_valid = False
                        reg = RegisterCommand(self.config, self.reddit)
                        self.logger.info("  sender not registered")
                        message = (f"❌ Sorry u/{comment.author.name} - you are not registered.  Please use "
                                   f"the [{reg.command_text} command]({self.config['e2t_post']}) to register.")

                user = next((u for u in USERS['users'] if u['username'].lower() == sender.lower()), None)
                if not user or int(amount) < 1:
                    weight = 0
                else:
                    weight = round(min(int(user['weight']) / self.config['comment2vote']['max_weight'], 1.0), 4)

                if is_valid:
                    # todo: uncomment with tip2vote
                    message = f"u/{sender} has tipped u/{recipient} {amount} {token} (weight: {weight})"
                    # message = f"u/{sender} has tipped u/{recipient} {amount} {token}"

                    if not recipient_exists:
                        self.logger.info("  parent is not registered")
                        message += (f"\n\n⚠️ u/{recipient} is not currently registered and will not receive "
                                    f"this tip unless they [register]({self.config['e2t_post']}) before this round ends.")

                tip = OffchainTip(sender, recipient, amount, weight, token,
                                  comment.fullname, comment.parent().fullname,
                                  comment.submission.id, community, is_valid, message)

                self.logger.info(f"  {tip}")
                tips.append(tip)

        return tips

    def handle_tip_status(self, comment):
        self.logger.info("  user checking status")

        result = database.get_user_by_name(comment.author.name)

        if not result or not result["address"]:
            self.logger.info("  user not registered")
            reg = RegisterCommand(self.config, self.reddit)
            self.leave_comment_reply(comment,
                                     f"Sorry u/{comment.author.name}, you are not registered.  Please use the {reg.command_text} command to register!")
            return

        sent_result = database.get_tips_sent_for_current_round_by_user(comment.author.name)
        received_result = database.get_tips_received_for_current_round_by_user(comment.author.name)
        funded_result = database.get_funded_for_current_round_by_user(comment.author.name)

        reply = f" u/{comment.author.name} has had the following tip activity this round:\n"
        if len(sent_result) == 0:
            reply += f"- **SENT:** u/{comment.author.name} 0 donut (0 tips sent)\n"
        else:
            # reply += f"- **SENT:** u/{comment.author.name} has **sent** the following earn2tips this round:\n\n"
            for tip in sent_result:
                amount = round(float(tip["amount"]), 5)
                reply += f"- **SENT:** {amount} {tip['token']} ({tip['count']} tips sent)\n"

        if len(received_result) == 0:
            # reply += f"\n\nu/{comment.author.name} has not **received** any earn2tips this round"
            reply += f"- **RECEIVED:** u/{comment.author.name} 0 donut (0 tips received)\n"
        else:
            # reply += f"\n\nu/{comment.author.name} has **received** the following earn2tips this round:\n\n"
            for tip in received_result:
                amount = round(float(tip["amount"]), 5)
                # reply += f"&ensp;&ensp;{amount} {tip['token']} ({tip['count']} total)\n\n"
                reply += f"- **RECEIVED:** {amount} {tip['token']} ({tip['count']} tips received)\n"

        if len(funded_result) > 0:
            # reply += f"\n\nu/{comment.author.name} has **funded** the following to their account this round:\n\n"
            for fund in funded_result:
                amount = round(float(fund["amount"]), 5)
                #reply += f"&ensp;&ensp;{amount} {fund['token']}\n\n"
                reply += f"- **FUNDED:** {amount} {fund['token']}\n\n"

        self.leave_comment_reply(comment, reply)

    def handle_tip_sub(self, comment):
        self.logger.info("  sub status")
        result = database.get_sub_status_for_current_round(comment.subreddit.display_name)

        if len(result) == 0:
            tip_text = f"Nobody has earn2tipped in r/{comment.subreddit.display_name} this round"
        else:
            tip_text = f"r/{comment.subreddit.display_name} has had the following earn2tip tips this round:\n\n"
            for tip in result:
                amount = round(float(tip["amount"]), 5)
                tip_text += f"&ensp;&ensp;{amount} {tip['token']} ({tip['tip_count']} tips total, {round(tip['average_tip_amount'], 2)} average)\n\n"

        community_tokens = self.config["community_tokens"]
        for ct in community_tokens:
            if ct["community"].lower() == f"r/{comment.subreddit.display_name.lower()}":
                valid_tokens = ct["tokens"]

        token_reply = f"\n\nValid tokens for r/{comment.subreddit.display_name} are:\n\n"
        for token in valid_tokens:
            token_reply += f"&ensp;&ensp;{token['name']} {' (default)' if token['is_default'] else ''}\n\n"

        self.leave_comment_reply(comment, tip_text + token_reply)

    def do_onchain_or_fallback_tip(self, comment):
        # just !tip (or some sort of edge case that fell through and will
        # get a default comment)

        # first get parent 'thing' information
        parent_author = comment.parent().author.name
        parent_result = database.get_user_by_name(parent_author)

        self.logger.info("  on-chain tipping (or fallback)")
        content_id = comment.parent().fullname
        desktop_link = f"https://www.donut.finance/tip/?action=tip&contentId={content_id}"

        if content_id[:3] == "t1_":
            desktop_link += f"&recipient={parent_author}&address={parent_result['address']}"

        mobile_link = f"https://metamask.app.link/dapp/{desktop_link}"

        comment_reply = f"**[Leave a tip]** [Desktop]({desktop_link}) | [Mobile (Metamask Only)]({mobile_link})"
        comment_reply += ("\n\n*The mobile link works best on iOS if you use the "
                          "System Default Browser in the Reddit Client (Settings > Open Links > Default Browser)*")
        self.leave_comment_reply(comment, comment_reply)

    def leave_comment_reply(self, comment, reply, set_processed=True, use_tip_thread=False, archive_result=None):
        sig = f'\n\n^(donut-bot {self.VERSION} | Learn more about [Earn2Tip]({self.config["e2t_post"]}))'

        if set_processed:
            database.set_processed_content(comment.fullname, Path(__file__).stem)

        if use_tip_thread:
            # check if post meta contains a central comment to attach tips to
            tip_thread_id = database.get_comment_thread_for_submission(comment.submission.fullname)
            if tip_thread_id:
                # we have a 'pinned' message that we should tuck this comment
                # under (instead of replying to this comment)
                # todo: uncomment for tip2vote
                if not archive_result['should_remove']:
                    link = f"https://reddit.com/comments/{comment.submission.id}/_/{comment.id}"
                    sig = f'\n\n[LINK]({link})' + sig

                    archive_link = (self.config['comment2vote']['archive_url']
                                    .replace('#y#', str(archive_result['year']))
                                    .replace('#m#', str(archive_result['month']))
                                    .replace('#d#', str(archive_result['day']))
                                    .replace('#f#', str(archive_result['filename'])))

                    sig = f'\n\n[ARCHIVE]({archive_link})' + sig
                    sig = f'\n(note: the archived content can take up to 30 minutes before it is available for viewing)' + sig

                reply += sig

                tip_thread = self.reddit.comment(tip_thread_id)
                tip_thread.reply(reply)
                return

        # if no central tip thread or not specified to use it then
        # reply directly to this comment
        reply += sig
        comment.reply(reply)

    def process_comment(self, comment):
        self.logger.info(f"process tip command - content_id: {comment.fullname} | author: {comment.author.name}")

        if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
            self.logger.info("  previously processed...")
            return

        self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")

        # maintain a fresh copy of the users file which will be used later to determine tip weight
        try:
            if "last_update" not in USERS or datetime.now() - timedelta(hours=self.config['comment2vote']['update_interval_hours']) >= USERS["last_update"]:
                USERS['users'] = json.load(urllib.request.urlopen(self.config['users_location']))
                USERS['last_update'] = datetime.now()
        except Exception as e:
            self.logger.error(f"  failed to download updated users file | {e}")
            pass

        # handle '!tip status' command
        if self.tip_status_regex.search(comment.body.lower()):
            self.handle_tip_status(comment)
            return

        # handle '!tip sub' command
        if self.tip_sub_regex.search(comment.body.lower()):
            self.handle_tip_sub(comment)
            return

        tips = self.parse_comments_for_tips(comment)
        if not tips:
            self.do_onchain_or_fallback_tip(comment)
            return

        reply = ""
        for idx, tip in enumerate(tips):
            reply += tip.message
            if idx < len(tips) - 1:
                reply += '\n\n'

        valid_tips = [t for t in tips if t.is_valid]
        if not valid_tips:
            self.leave_comment_reply(comment, reply)
        elif database.process_earn2tips(valid_tips, Path(__file__).stem):
            self.logger.info("  success...")
            archive_result = self.archive_comment(comment, max(valid_tips, key=lambda x: x.amount).amount)
            self.leave_comment_reply(comment, reply, False, True, archive_result)

            # todo: uncomment for tip2vote
            # if archive_result['should_remove']:
            #    comment.mod.remove(spam=False)
        else:
            self.leave_comment_reply(comment, f"❌ Sorry u/{comment.author.name}, I was unable to process your "
                                              f"tip at this time.  Please try again later!")

    def archive_comment(self, comment, max_tip):
        """
        Archives the given comment if meets requirements.
        :param comment: The comment to archive
        :param max_tip: The max tip amount from all tips sent in this comment
        :return: A dict containing all the portions of the archive path
        """
        tip_directory = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"../tip_archive/"))
        created_utc = datetime.utcfromtimestamp(comment.created_utc)

        save_dir = f'{tip_directory}/{created_utc.year}/{created_utc.month:02}/{created_utc.day:02}'
        os.makedirs(save_dir, exist_ok=True)

        # archive_text = f'author: {comment.author}\ndate: {created_utc} UTC\n\n{comment.body}'

        filename = comment.fullname + ".txt"
        with open(os.path.join(save_dir, filename).replace('\\', '/'), 'w') as f:
            f.write(comment.body)  # could also use body_html

        should_remove = False
        if len(comment.body) <= 50:
            should_remove = True

        if max_tip >= self.config['comment2vote']['min_tip_to_avoid_archive']:
            should_remove = False

        return {
            'should_remove': should_remove,
            'year': created_utc.year,
            'month': f'{created_utc.month:02}',
            'day': f'{created_utc.day:02}',
            'filename': filename,
        }
