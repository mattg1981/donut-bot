import json
import logging
import os
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import praw
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from cache import cache


def get_submission_topic(submission, topics, community):
    # test if this submission hits any topics that are limited in this community
    for topic in [t for t in topics if t["community"].lower() == community.lower()]:
        topic_ignore = []
        for ignore in topic["overrides"]["ignore"]:
            if not ignore.startswith("t3_"):
                topic_ignore.append("t3_" + ignore)
            else:
                topic_ignore.append(ignore)

        topic_include = []
        for include in topic["overrides"]["include"]:
            if not include.startswith("t3_"):
                topic_include.append("t3_" + include)
            else:
                topic_include.append(include)

        if submission.fullname in topic_ignore:
            continue

        if submission.fullname in topic_include:
            return topic

        # otherwise test the title against the patterns
        for pattern in topic["patterns"]:
            submission_match = re.search(pattern, submission.title.lower())
            if submission_match:
                return topic


def is_daily(submission):
    return (
        "daily general discussion - " in submission.title.lower()
        and "(utc+0)" in submission.title.lower()
    )


def build_sticky_comment(submission, topic):
    reply_message = (
        f"{submission.author.name}, this comment  logs the Pay2Post fee, an anti-spam mechanism where a "
        f"DONUT 'tax' is deducted from your distribution share for each post submitted. Learn more ["
        f"here](https://www.reddit.com/r/ethtrader/comments/199ht5i"
        f"/governance_poll_dynamic_pay2post_fee_target/)."
        f"\n\ncc: u/pay2post-ethtrader\n\n"
        f"----------\n\n"
    )

    if not is_daily(submission):
        onchain_link = (
            f"https://www.donut.finance/tip/?action=tip&contentId={submission.fullname}"
        )

        if topic:
            reply_message += f"Topic: {topic['display_name']}\n\n"
            reply_message += "Learn more about topics limits [here](https://www.reddit.com/r/ethtrader/comments/1fyb8rv/rethtrader_automated_topic_limiter_topics_allowed/).\n\n"
            reply_message += "----------\n\n"

        reply_message += "Understand how Donuts and tips work by reading the [beginners guide](https://www.reddit.com/r/ethtrader/comments/1ftnx4t/megathread_comprehensive_guide_to_rethtrader/).\n\n"
        reply_message += "----------\n\n"

        reply_message += f"[Click here to tip this post on-chain]({onchain_link})\n\n"
        # reply_message += "Tip confirmations below.\n\n"

        logger.info("  send reply...")
        reply = submission.reply(reply_message)

        logger.info("  distinguish comment...")
        reply.mod.distinguish(sticky=True)
        return reply.fullname


def create_post_meta(submission, comment_thread_id):
    logger.info("  store meta in db...")

    author = submission.author
    if submission.author:
        author = submission.author.name

    with sqlite3.connect(db_path) as db:
        sql = """
            INSERT INTO post (submission_id, tip_comment_id, author, is_daily, created_date, community)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        cursor = db.cursor()
        cursor.execute(
            sql,
            [
                submission.fullname,
                comment_thread_id,
                author,
                is_daily(submission),
                datetime.utcfromtimestamp(submission.created_utc),
                submission.subreddit.display_name.lower(),
            ],
        )

    logger.info("  done.")


def eligible_to_submit(submission):
    max_posts_per_24_hours = int(config["posts"]["max_per_24_hours"])
    post_cooldown_in_minutes = int(config["posts"]["post_cooldown_in_minutes"])

    post_per_day_sql = f"""
        select count(*) < {max_posts_per_24_hours} as eligible_to_post
        from post
        where 
            author = ?
            and tip_comment_id is not null
            and created_date >= datetime('now','-24 hour');
    """

    post_cooldown_sql = f"""
        select post.created_date <= datetime('now', '-{post_cooldown_in_minutes} minute') as eligible_to_post_cooldown 
        from post
        where author = ? and tip_comment_id is not null
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

    if eligibility_check and not eligibility_check["eligible_to_post"]:
        can_post = False
        submission.reply(
            f"Sorry u/{submission.author.name}, you may only submit {max_posts_per_24_hours} posts per a "
            f"24-hour window.  Please try again later.\n\nYou may also use the `!post status` command to "
            f"check your posting eligibility."
        )

    if (
        can_post
        and post_cooldown_check
        and not post_cooldown_check["eligible_to_post_cooldown"]
    ):
        can_post = False
        submission.reply(
            f"Sorry u/{submission.author.name}, you may only submit a new post every "
            f"{post_cooldown_in_minutes} minutes!  Please try again later.\n\nYou may also use the "
            f"`!post status` command to check your posting eligibility."
        )

    if not can_post:
        create_post_meta(submission, None)
        submission.mod.lock()
        submission.mod.remove(spam=False)
        return False

    return True


def previously_processed(submission, bot_name):
    sql = """
            select *
            from post
            where submission_id = ?
        """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(sql, [submission.fullname])
        db_result = cursor.fetchone()

    if db_result:
        return db_result

    # to address the reddit API (or praw) returning historically old posts.  Most posts will already
    # be handled by the database lookup we just performed.  However, if the post was rejected for word count
    # or other edge cases, no record is recorded in the database.  To handle these, we will search
    # the comments of this post to see if donut-bot has responded on the top-level
    # previously.  If it has, then this post has been previously processed.

    submission.comment_sort = "old"
    submission.comments.replace_more(limit=None)

    for c in submission.comments:  # Top-level only
        # c.author may be None if the user was deleted
        if c.author and c.author.name == bot_name:
            return True

    return False


if __name__ == "__main__":
    # load environment variables
    load_dotenv()

    # load config
    with open(os.path.normpath("../config.json"), "r") as f:
        config = json.load(f)

    # set up logging
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("post_bot")
    logger.setLevel(logging.INFO)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(base_dir, "../logs/post-bot.log")
    handler = RotatingFileHandler(
        os.path.normpath(log_path), maxBytes=2500000, backupCount=4
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # get database location
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    username = os.getenv("REDDIT_USERNAME")

    # creating an authorized reddit instance
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=username,
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent="post-bot (by u/mattg1981)",
    )

    subs = ""
    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]
        subs += community
        if idx < len(config["community_tokens"]) - 1:
            subs += "+"

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

                try:
                    logger.info(f"processing submission by [{submission.author.name}]: {submission.fullname} [{submission.title}]")
                except Exception as e:
                    logger.error("error processing submission: {e})")

                if previously_processed(submission, username):
                    logger.info(f"  {submission.fullname} already processed.")
                    continue

                community = submission.subreddit.display_name.lower()

                logger.info(
                    f"  is_reddit_media_domain: {submission.is_reddit_media_domain}"
                )

                post_hint = None

                try:
                    logger.info(f"  post_hint: {submission.post_hint}")
                    post_hint = submission.post_hint
                except Exception as e:
                    logger.info(f"  post_hint is not present...")

                special_membership_required = False
                if post_hint and not 'self' in post_hint and not 'link' in post_hint:
                    logger.info('    special membership required for this post_hint...')
                    special_membership_required = True

                if submission.is_reddit_media_domain or special_membership_required:
                    if not cache.is_special_member(submission.author.name, community):

                        logger.info(
                            f"  is_special_member => false; removed..."
                        )

                        submission.reply(
                            f"Your post was removed from r/{community} because media posts are reserved for special "
                            f"members. Please visit [this link] (https://donut-dashboard.com/#/membership) to learn "
                            f"more or to purchase a membership.  Otherwise, you can re-submit with a link to the "
                            f"media in the body of the post."
                        )
                        submission.mod.lock()
                        submission.mod.remove(spam=False)
                        continue

                    else:
                        logger.info(
                            f"  is_reddit_media_domain => true and special member => true; allow..."
                        )

                excluded = False
                for excluded_flair in config["posts"][
                    "minimum_word_count_excluded_flairs"
                ]:
                    if "[" + excluded_flair.lower() + "]" in submission.title.lower():
                        excluded = True
                        break

                # exclude word count minimum and topic limiting for users in ignore_list
                post_topic = None
                if submission.author.name.lower() not in ignore_list:
                    # exclude word count minimum if using a standardized title
                    for title in config["posts"]["bypass_word_count_by_title"]:
                        if title.lower() in submission.title.lower():
                            excluded = True

                    if (
                        not excluded
                        and submission.is_self
                        and len(submission.selftext.split())
                        < config["posts"]["minimum_word_count"]
                    ):
                        logger.info(
                            f"  removed due to minimum_word_count={config['posts']['minimum_word_count']}"
                        )

                        create_post_meta(submission, None)

                        submission.reply(
                            f"Your post was removed from r/{community} because it's too short (minimum of "
                            f"{config['posts']['minimum_word_count']} words). You can still see it, but nobody else "
                            f"can. Feel free to resubmit your post with more text in the body to help direct the "
                            f"discussion. Thanks!"
                        )
                        submission.mod.lock()
                        submission.mod.remove(spam=False)
                        continue

                    # refresh topic limits
                    if (
                        "last_update" not in TOPIC_LIMITS
                        or datetime.now() - timedelta(minutes=6)
                        >= TOPIC_LIMITS["last_update"]
                    ):
                        logger.info("  update TOPIC_LIMITS...")
                        TOPIC_LIMITS["last_update"] = datetime.now()
                        try:
                            TOPIC_LIMITS["topics"] = json.load(
                                urllib.request.urlopen(
                                    "https://raw.githubusercontent.com/EthTrader/topic-limiting/main/topic_meta.json"
                                )
                            )
                        except Exception:
                            logger.error("Failed to load topic_meta - invalid .json")

                        try:
                            TOPIC_LIMITS["limits"] = json.load(
                                urllib.request.urlopen(
                                    "https://raw.githubusercontent.com/EthTrader/topic-limiting/main/topic_limits.json"
                                )
                            )
                        except Exception:
                            logger.error("Failed to load topic_limits - invalid .json")

                    topics = TOPIC_LIMITS["topics"]
                    limits = TOPIC_LIMITS["limits"]["data"]

                    # topic limiting is performed before create_post_meta - so if a post is removed for
                    # being limited, it will not count against the XX posts per day limit
                    post_topic = get_submission_topic(submission, topics, community)

                    if post_topic:
                        logger.info(f"  topic detected: {post_topic['display_name']}")
                        topic_meta = next(
                            t
                            for t in limits
                            if t["display_name"] == post_topic["display_name"]
                            and t["community"] == community
                        )

                        if topic_meta["current"] >= topic_meta["limit"]:
                            logger.info(
                                f"  removed due to topic limiting: {topic_meta}"
                            )
                            create_post_meta(submission, None)
                            submission.reply(
                                f"Sorry u/{submission.author.name}, topic limiting is in effect and only allows "
                                f"{topic_meta['limit']} posts about **{topic_meta['display_name']}** "
                                f"in the Hot 50 at a given time. Please try again later..."
                            )
                            submission.mod.lock()
                            submission.mod.remove(spam=False)
                            continue

                # todo: currently, eligible_to_submit will remove the post but would read better if
                #  that logic was performed here
                if submission.author.name.lower() in ignore_list or eligible_to_submit(
                    submission
                ):
                    comment_thread_id = build_sticky_comment(submission, post_topic)
                    create_post_meta(submission, comment_thread_id)

        except Exception as e:
            logger.error(e)
            logger.info("sleeping 30 seconds ...")
            time.sleep(30)
