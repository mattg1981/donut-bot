import json
import os.path
import urllib.request
import sqlite3
import praw

from datetime import datetime
from dotenv import load_dotenv

if __name__ == '__main__':
    print('begin...')

    # load environment variables
    load_dotenv()

    with open(os.path.normpath("../config.json"), 'r') as c:
        config = json.load(c)

    # creating an authorized reddit instance
    reddit = praw.Reddit(client_id=os.getenv('REDDIT_CLIENT_ID'),
                         client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                         username=os.getenv('REDDIT_USERNAME'),
                         password=os.getenv('REDDIT_PASSWORD'),
                         user_agent='potd-bot (by u/mattg1981)')

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    now = datetime.now()
    this_week = int(datetime.now().strftime("%U")) + 1

    potd_json = json.load(urllib.request.urlopen("https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/posts/potd_current.json"))

    last_update = datetime.fromtimestamp(potd_json['last_update'])
    last_update_week = int(potd_json['last_update_week'])

    # check if we have already calculated the potd for last week
    if this_week == last_update_week:
        pass # exit(0)

    dist_round_query = """
            select distribution_round from distribution_rounds
            where DATETIME() between from_date and to_date;
        """

    sql = """
        select week_number,
               year,
               post_id,
               res.weight,
               votes,
               count(e2t.id) as tips,
               sum(e2t.amount) as tips_sum,
               ROW_NUMBER() OVER (ORDER BY res.weight desc) as 'rank'
        from (select strftime('%W', created_date) as 'week_number',
        					strftime('%Y', created_date) as 'year',
                     post_id,
                     sum(weight)                  as 'weight',
                     count(id)                    as 'votes'
              from potd
              where cast(strftime('%W', created_date) as int) = cast(strftime('%W', datetime()) as int) - 1
                AND cast(strftime('%Y', created_date) as int) = cast(strftime('%Y', datetime()) as int)
              group by strftime('%W', created_date), post_id
              order by sum(weight) desc) res
        left join earn2tip e2t on e2t.parent_content_id = res.post_id
        group by res.post_id
        order by res.weight desc
        limit 4;
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()

        cur.execute(dist_round_query)
        dist_round = int(cur.fetchall()[0]['distribution_round'])

        cur.execute(sql, )
        query_result = cur.fetchall()

    try:
        potd_winners_this_round = json.load(urllib.request.urlopen(
            f"https://raw.githubusercontent.com/mattg1981/donut-bot-output/main/posts/potd_round_{dist_round}.json"))
    except Exception as e:
        print(f'potd_current_round not found: {e}')
        potd_winners_this_round = []

    potd_results = {
        'last_update': int(now.timestamp()),
        'last_update_week': this_week,
        'winners': []
    }

    for post in query_result:
        submission = reddit.submission(id=post['post_id'][3:])

        try:
            shortlink = submission.shortlink
            author = submission.author.name
            title = submission.title
            created_date = int(submission.created_utc)
            flair = submission.link_flair_text
            #selftext = submission.selftext.replace('"', '\'')
            upvotes = submission.ups
        except Exception:
            shortlink = shortlink if shortlink else None
            author = author if author else None
            title = title if title else None
            created_date = created_date if created_date else None
            flair = flair if flair else None
            #selftext = selftext if selftext else None
            upvotes = upvotes if upvotes else None


        potd_results['last_update_week'] = this_week
        potd_results["winners"].append({
            'rank': post['rank'],
            'nominations': post['votes'],
            'weight': post['weight'],
            'week_number': int(post['week_number']),
            'year': int(post['year']),
            'post': {
                'post_id': post['post_id'],
                'author': author,
                'reddit_upvotes': upvotes,
                'title': title,
                'tips': post['tips'],
                'tips_amount': post['tips_sum'] or 0,
                'url': shortlink,
                'created_date': datetime.fromtimestamp(created_date),
                'flair': flair
            }
        })

        potd_winners_this_round.append({
            'week_number': int(post['week_number']),
            'year': int(post['year']),
            'rank': post['rank'],
            'author': author,
            'post_id': post['post_id'],
        })


    current_file = "../temp/potd_current.json"
    round_file = f"../temp/potd_round_{dist_round}.json"

    if os.path.exists(current_file):
        os.remove(current_file)

    if os.path.exists(round_file):
        os.remove(round_file)

    with open(current_file, 'w') as f:
        json.dump(potd_results, f, indent=4, default=str)

    with open(round_file, 'w') as f:
        json.dump(potd_winners_this_round, f, indent=4, default=str)


