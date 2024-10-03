import json
import os.path
import re
import time
import urllib.request
import praw
from dotenv import load_dotenv

if __name__ == '__main__':
    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as conf:
        config = json.load(conf)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         user_agent='topic-limiter (by u/mattg1981)')

    reddit.read_only = True

    topics = json.load(urllib.request.urlopen("https://raw.githubusercontent.com/EthTrader/topic-limiting/main"
                                              "/topic_meta.json"))

    topic_results = []

    for idx, community_token in enumerate(config["community_tokens"]):
        community = community_token["community"]
        if "r/" in community:
            community = community[2:]

        for post in reddit.subreddit(community).hot(limit=50):
            for topic in topics:

                if topic["community"] != community:
                    continue

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

                if post.fullname in topic_ignore:
                    # skip to the next topic
                    continue

                # add 'current' field to the topic meta
                # this will be incremented as we come across submissions that hit on that topic
                if "current" not in topic:
                    topic["current"] = 0

                if "submissions" not in topic:
                    topic["submissions"] = []

                # override says this post should be included in this topic
                if post.fullname in topic_include:
                    topic["current"] += 1
                    topic["submissions"].append(post.shortlink)
                    break

                # otherwise test all the patterns
                topic_match = False
                for pattern in topic["patterns"]:
                    hot_match = re.search(pattern, post.title.lower())
                    if hot_match:
                        topic["current"] += 1
                        topic_match = True
                        topic["submissions"].append(post.shortlink)
                        break

                if topic_match:
                    break

        topic_results.extend([
            {
                "display_name": t["display_name"],
                "limit": t["limit"],
                "current": t["current"],
                "submissions": t["submissions"],
                "community": community
            } for t in topics])

        out_file = f"../temp/topic_limits.json"

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump({'last_update': int(time.time()), 'data': topic_results}, f, indent=4)
