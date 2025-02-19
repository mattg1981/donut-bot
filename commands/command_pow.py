from pathlib import Path

from praw.models import Comment

from cache import cache
from commands import Command
from config import Community
from database import database


def is_eligible_to_cast_vote(author, post_id, community):
    eligibility_results = database.get_potd_eligible(author, post_id, community.name)

    e = [e for e in eligibility_results if e['potd_eligibile'] == 0]
    if len(e):
        return 0, e[0]['reason']

    weight = cache.get_user_weight(author)

    if weight < community.posts.pow_min_weight:
        return 0, 'you do not have sufficient governance weight to perform this action.'

    return 1, 'ok', min(weight, community.posts.pow_max_weight)


class PostOfTheWeekCommand(Command):
    def __init__(self):
        super(PostOfTheWeekCommand, self).__init__()
        self.command_text = "!pow"

    def leave_comment_reply(self, comment, reply):
        sticky_thread = None
        try:
            sticky_thread_id = database.get_comment_thread_for_submission(comment.submission.fullname)
            if sticky_thread_id:
                sticky_thread = self.reddit.comment(sticky_thread_id)
        except Exception as e:
            self.logger.error(e)

        if sticky_thread is None:
            sticky_thread = comment

        database.set_processed_content(comment.fullname, Path(__file__).stem)
        sticky_thread.reply(reply)

    def process_comment(self, comment: Comment, author: str, community: Community) -> None:

        if comment.parent_id is None or not comment.parent_id[:3].lower() == 't3_':
            comment.reply(f"Sorry u/{author}, this command can only be used to vote for posts!")
            return

        is_eligible, reason, weight = is_eligible_to_cast_vote(author, comment.parent_id, community)

        if not is_eligible:
            self.leave_comment_reply(comment, f"Sorry u/{author}, {reason}")
            return

        database.insert_potd_vote(comment.parent_id, author, weight, community.name)

        comment.reply(f"Thank you u/{author}, your post-of-the-week nomination has been recorded!")
