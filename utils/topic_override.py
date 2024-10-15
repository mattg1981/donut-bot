import json
import os
import sqlite3
import sys
from datetime import datetime

import praw
from dotenv import load_dotenv


def eligible_to_submit(submission):
    max_posts_per_24_hours = int(config['posts']['max_per_24_hours'])
    post_cooldown_in_minutes = int(config['posts']['post_cooldown_in_minutes'])

    post_per_day_sql = f"""
        select count(*) < {max_posts_per_24_hours} as eligible_to_post
        from post
        where author = ?
          and created_date >= datetime('now','-24 hour');
    """

    post_cooldown_sql = f"""
        select post.created_date <= datetime('now', '-{post_cooldown_in_minutes} minute') as eligible_to_post_cooldown 
        from post
        where author = ?
        order by created_date desc
        limit 1;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(post_per_day_sql, [submission.author.name])
        eligibility_check = cursor.fetchone()

        cursor.execute(post_cooldown_sql, [submission.author.name])
        post_cooldown_check = cursor.fetchone()

    can_post = True

    if eligibility_check and not eligibility_check['eligible_to_post']:
        can_post = False
        print("user is in 24-hour window cooldown currently...")
        submission.reply(f"Sorry u/{submission.author.name}, you may only submit {max_posts_per_24_hours} posts per a "
                         f"24-hour window.  Please try again later.\n\nYou may also use the `!post status` command to "
                         f"check your posting eligibility.")

    if can_post and post_cooldown_check and not post_cooldown_check['eligible_to_post_cooldown']:
        can_post = False
        print("user is in post cooldown currently...")
        submission.reply(f"Sorry u/{submission.author.name}, you may only submit a new post every "
                         f"{post_cooldown_in_minutes} minutes!  Please try again later.\n\nYou may also use the "
                         f"`!post status` command to check your posting eligibility.")

    return can_post


def is_daily(submission):
    return "daily general discussion - " in submission.title.lower() and "(utc+0)" in submission.title.lower()


def build_sticky_comment(submission):
    reply_message = (f"{submission.author.name}, this comment  logs the Pay2Post fee, an anti-spam mechanism where a "
                     f"DONUT 'tax' is deducted from your distribution share for each post submitted. Learn more ["
                     f"here](https://www.reddit.com/r/ethtrader/comments/199ht5i"
                     f"/governance_poll_dynamic_pay2post_fee_target/)."

                     f"\n\ncc: u/pay2post-ethtrader\n\n"
                     f"----------\n\n")

    if not is_daily(submission):
        onchain_link = f"https://www.donut.finance/tip/?action=tip&contentId={submission.fullname}"

        reply_message += f"Understand how Donuts and tips work by reading the [beginners guide](https://www.reddit.com/r/ethtrader/comments/1ftnx4t/megathread_comprehensive_guide_to_rethtrader/).\n\n"
        reply_message += "----------\n\n"

        reply_message += f"[Click here to tip this post on-chain]({onchain_link})\n\n"

        print(f"  create reply...")
        reply = submission.reply(reply_message)

        print(f"  distinguish comment...")
        reply.mod.distinguish(sticky=True)
        return reply.fullname


def update_post_meta(submission, comment_thread_id):
    print(f"  update meta...")

    db_result = submission.author
    if submission.author:
        author = submission.author.name

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()

        exists_sql = """
            SELECT * 
            FROM post
            WHERE submission_id=?;
        """

        cursor.execute(exists_sql, [submission.fullname])
        exists = cursor.fetchone()

        if exists:
            sql = """
                UPDATE post 
                SET tip_comment_id=?
                WHERE submission_id=?;
            """

            cursor.execute(sql, [comment_thread_id, submission.fullname])
        else:
            author = submission.author
            if submission.author:
                author = submission.author.name

            insert_sql = """
                        INSERT INTO post (submission_id, tip_comment_id, author, is_daily, created_date, community)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """

            cursor.execute(insert_sql, [submission.fullname,
                                        comment_thread_id,
                                        author,
                                        is_daily(submission),
                                        datetime.utcfromtimestamp(submission.created_utc),
                                        submission.subreddit.display_name.lower()])

    print(f"  done.")


if __name__ == '__main__':
    print(f"{sys.argv=}")

    if len(sys.argv) != 2:
        print("Usage: topic_override.py <submission> (example: topic_override.py 1g4b01h)")
        exit(4)

    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=os.getenv('REDDIT_USERNAME'),
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent='post-bot topic override (by u/mattg1981)')

    submission = reddit.submission(id=sys.argv[1])

    if eligible_to_submit(submission):
        comment_thread_id = build_sticky_comment(submission)
        update_post_meta(submission, comment_thread_id)
        submission.mod.approve()
        submission.mod.unlock()
