# import json
# import urllib.request
#
# from datetime import datetime, timedelta
# from pathlib import Path
# from database import database
# from commands.command import Command
#
# GOVERNANCE_WEIGHT = {}
# MIN_WEIGHT_REQUIRED_TO_PARTICIPATE = 20_000
# MAX_WEIGHT_PER_VOTE = 500_000
#
# class PotdCommand(Command):
#     VERSION = 'v0.1.20240508-potd'
#     SIGNATURE = f'\n\n^(donut-bot {VERSION})'
#
#     def __init__(self, config, reddit):
#         super(PotdCommand, self).__init__(config, reddit)
#         self.command_text = "!potd"
#
#     def is_eligible(self, name, post_id, community):
#         eligibility_results = database.get_potd_eligible(name, post_id, community)
#
#         e = [e for e in eligibility_results if e['potd_eligibile'] == 0]
#         if len(e):
#             return {
#                 'is_eligible': 0,
#                 'response': e[0]['reason']
#             }
#
#         user = next((u for u in GOVERNANCE_WEIGHT['users'] if u['username'].lower() == name.lower()), None)
#         if not user or int(user['weight']) < MIN_WEIGHT_REQUIRED_TO_PARTICIPATE:
#             return {
#                 'is_eligible': 0,
#                 'response': 'you do not have sufficient governance weight to perform this action.',
#             }
#
#         return {
#             'is_eligible': 1,
#             'response': 'ok',
#             'weight': int(user['weight'])
#         }
#
#     def leave_comment_reply(self, comment, reply):
#         sticky_thread = None
#         try:
#             sticky_thread_id = database.get_comment_thread_for_submission(comment.submission.fullname)
#             if sticky_thread_id:
#                 sticky_thread = self.reddit.comment(sticky_thread_id)
#         except Exception as e:
#             self.logger.error(e)
#
#         if sticky_thread is None:
#             sticky_thread = comment
#
#         link = f"https://reddit.com/comments/{comment.submission.id}/_/{comment.id}"
#         reply += f'\n\n[LINK]({link})' + self.SIGNATURE
#         database.set_processed_content(comment.fullname, Path(__file__).stem)
#         sticky_thread.reply(reply)
#
#     def process_comment(self, comment):
#         self.logger.info(f"process potd command - content_id: {comment.fullname} | author: {comment.author.name}")
#
#         if database.has_processed_content(comment.fullname, Path(__file__).stem) is not None:
#             self.logger.info("  previously processed...")
#             return
#
#         self.logger.info(f"  comment link: https://reddit.com/comments/{comment.submission.id}/_/{comment.id}")
#
#         user = comment.author.name
#
#         try:
#
#             if comment.parent_id is None or not comment.parent_id[:3].lower() == 't3_':
#                 self.leave_comment_reply(comment, f"Sorry u/{user}, this command can only be used to vote for posts!")
#                 return
#
#             # update governance weight (if needed)
#             if ("last_update" not in GOVERNANCE_WEIGHT or
#                     datetime.now() - timedelta(hours=8) >= GOVERNANCE_WEIGHT["last_update"]):
#
#                 GOVERNANCE_WEIGHT['users'] = json.load(urllib.request.urlopen(self.config["users_location"]))
#                 GOVERNANCE_WEIGHT['last_update'] = datetime.now()
#
#             community = comment.subreddit.display_name.lower()
#
#             eligibility_check = self.is_eligible(user, comment.parent_id, community)
#             if not eligibility_check['is_eligible']:
#                 self.leave_comment_reply(comment, f"Sorry u/{user}, {eligibility_check['response']}")
#                 return
#
#             database.insert_potd_vote(comment.parent_id,
#                                       user,
#                                       min(eligibility_check['weight'], MAX_WEIGHT_PER_VOTE),
#                                       community)
#
#             self.leave_comment_reply(comment, f"Thank you u/{user}, your post-of-the-week nomination has been recorded!")
#         except Exception as e:
#             self.logger.error(e)
#             self.leave_comment_reply(comment, f"An error occurred processing your action.  Please try again later.")
#
