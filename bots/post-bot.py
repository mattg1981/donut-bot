import json
import logging
import os
import sqlite3
import time
import re
import urllib.request
import praw

from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv


def get_submission_topic(submission, topics, community):
    # test if this submission hits any topics that are limited
    for topic in [t for t in topics if t["community"].lower() == community.lower()]:
        for t in topic["patterns"]:
            submission_match = re.search(t, submission.title.lower())
            if submission_match:
                return topic


def is_daily(submission):
    return "daily general discussion - " in submission.title.lower() and "(utc+0)" in submission.title.lower()


def build_sticky_comment(submission, topic):
    logger.info(f"processing submission: {submission.fullname} [{submission.title}]")

    reply_message = ""

    if is_daily(submission):
        onchain_link = f"https://www.donut.finance/tip/?action=tip&contentId={submission.fullname}"
        if topic:
            reply_message += f"This post had the **{topic['display_name']}** topic assigned.\n\n"
            reply_message += "----------"

        reply_message += f"[Tip this post.]({onchain_link})\n\n"
        reply_message += "On-chain and off-chain tip confirmations below.\n\n"

        reply_message += """----------
            \n\n

    **New Voting and Reward System**

    To promote quality content and reduce spam, we've implemented a new tip-voting system! Here's how it works:

    1. **Upvoting with Tips:**
       * Use the `!tip` command to upvote comments/posts. These are special upvotes that determine a user's DONUT reward at the end of the month.
       * Example: `!tip 5` to tip 5 DONUTS.
       * Any tip of 1 or more DONUTS counts as 1 vote.
    2. **Weighted Votes:**
       * Vote weight is based on your [governance score](https://donut-dashboard.com/#/governance).
       * A governance score of 20K or more has a full vote weight (1.0).
       * Scores below 20K have a proportional weight (e.g., 1K score = 0.05 weight).
    3. **Anti-Spam Measures:**
       * Comments with tips below 5 DONUTS and less than 12 characters will be removed, but the vote will still count.
       * All tips are recorded under a stickied comment for transparency, including tips included in removed comments.
    4. **Transparency:**
       * Tip records will look like this:

          `u/[username] tipped u/[anotheruser] 1.0 DONUT (weight: 0.4) [ARCHIVE](link to snapshot)`

    **Guidelines:**

    * Tip votes should be based solely on the quality of the content, not on the author or expectations of reciprocation.
    * As a tipper, you are acting as a judge, ensuring that valuable contributions are rewarded impartially.
    * Quid pro quo tipping behavior will be penalized. Moderators will monitor tips for misuse and take appropriate action.

    Let's make EthTrader a better place by contributing valuable content and rewarding it fairly! 🚀
            """

        logger.info(f"  send reply...")
        reply = submission.reply(reply_message)

        logger.info(f"  distinguish comment...")
        reply.mod.distinguish(sticky=True)
        return reply.fullname


def create_post_meta(submission, comment_thread_id):
    logger.info(f"  store meta in db...")

    author = submission.author
    if submission.author:
        author = submission.author.name

    with sqlite3.connect(db_path) as db:
        sql = """
            INSERT INTO post (submission_id, tip_comment_id, author, is_daily, created_date, community)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor = db.cursor()
        cursor.execute(sql, [submission.fullname,
                             comment_thread_id,
                             author,
                             is_daily(submission),
                             datetime.utcfromtimestamp(submission.created_utc),
                             submission.subreddit.display_name.lower()])

    logger.info(f"  done.")


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

    if not eligibility_check['eligible_to_post']:
        can_post = False
        submission.reply(
            f"Sorry u/{submission.author.name}, you may only submit {max_posts_per_24_hours} posts per a 24-hour window.  "
            f"Please try again later.\n\nYou may also use the `!post status` command to check your posting eligibility.")

    if not post_cooldown_check['eligible_to_post_cooldown']:
        can_post = False
        submission.reply(
            f"Sorry u/{submission.author.name}, you may only submit a new post every {post_cooldown_in_minutes} minutes!  "
            f"Please try again later.\n\nYou may also use the `!post status` command to check your posting eligibility.")

    if not can_post:
        submission.mod.lock()
        submission.mod.remove(spam=False)
        return False

    return True


def previously_processed(submission):
    sql = f"""
            select *
            from post
            where submission_id = ? and community = ?
        """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(sql, [submission.fullname, submission.subreddit.display_name.lower()])
        return cursor.fetchone()


if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), 'r') as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("post_bot")
    logger.setLevel(logging.INFO)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/post-bot.log")
    handler = RotatingFileHandler(os.path.normpath(log_path), maxBytes=2500000, backupCount=4)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    username = os.getenv('REDDIT_USERNAME')

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=username,
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent='post-bot (by u/mattg1981)')

    subs = ""
    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]
        subs += community
        if idx < len(config["community_tokens"]) - 1:
            subs += '+'

    # users listed in ignore_list are not restricted to a limited number of posts
    # be sure to user lowercase when adding to this list
    ignore_list = ["ethtrader_reposter", "automoderator"]

    TOPIC_LIMITS = {}

    while True:
        try:
            # for submission in reddit.subreddit(subs).stream.submissions():
            for submission in reddit.subreddit(subs).stream.submissions(skip_existing=True):
                if submission is None:
                    continue

                if not submission.author or submission.author.name == username:
                    continue

                if previously_processed(submission):
                    logger.info(f"  {submission.fullname} already processed.")
                    continue

                # refresh topic limits
                # if ("last_update" not in TOPIC_LIMITS or datetime.now() - timedelta(minutes=5) >=
                #         TOPIC_LIMITS["last_update"]):
                #     TOPIC_LIMITS['last_update'] = datetime.now()
                #     TOPIC_LIMITS['topics'] = json.load(urllib.request.urlopen(
                #         "https://raw.githubusercontent.com/EthTrader/topic-limiting/main/topic_meta.json"))
                #     TOPIC_LIMITS['limits'] = json.load(urllib.request.urlopen(
                #         "https://raw.githubusercontent.com/EthTrader/topic-limiting/main/topic_limits.json"))
                #
                # topics = TOPIC_LIMITS['topics']
                # limits = TOPIC_LIMITS['limits']['data']
                #
                # # topic limiting is performed before create_post_meta - so if a post is removed for
                # # being limited, it will not count against the XX posts per day limit
                # community = submission.subreddit.display_name.lower()
                # post_topic = get_submission_topic(submission, topics, community)
                #
                # if post_topic:
                #     current_topic = next(t for t in limits if t['display_name'] == post_topic['display_name'] and
                #                          t['community'] == community)
                #     if current_topic["current"] >= current_topic["limit"]:
                #         submission.reply(
                #             f"Sorry u/{submission.author.name}, topic limiting is in effect and only allows "
                #             f"{current_topic['allowance']} posts about **{current_topic['display_name']}** "
                #             f"to be in the Hot50. Please try again later.")
                #         submission.mod.lock()
                #         submission.mod.remove(spam=False)

                # todo: currently, eligible_to_submit will remove the post but would read better if
                #  that logic was performed here
                if submission.author.name.lower() in ignore_list or eligible_to_submit(submission):
                    # comment_thread_id = build_sticky_comment(submission, post_topic)
                    comment_thread_id = build_sticky_comment(submission, None)
                    create_post_meta(submission, comment_thread_id)

        except Exception as e:
            logger.error(e)
            logger.info('sleeping 30 seconds ...')
            time.sleep(30)
