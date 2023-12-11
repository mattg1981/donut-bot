import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    rounds_query = """
        select distribution_round from distribution_rounds
        where DATE() between from_date and to_date;
    """

    tips_query = """
    select
      e.from_user, 
      e.to_user,
      e.amount,
      e.token,
      e.content_id,
      e.parent_content_id,
      e.submission_content_id,
      e.community,
      e.created_date
    from
      earn2tip e
    where
      created_date between (
        select
          from_date
        from
          distribution_rounds
        where
          distribution_round = ?
      ) and (
        select
          to_date
        from
          distribution_rounds
        where
          distribution_round = ?
      );
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(rounds_query)
        round_result = cursor.fetchone()

    # build tips for last round and current round
    r_min = int(round_result["distribution_round"]) - 1
    r_max = int(round_result["distribution_round"])

    for i in range(r_min, r_max + 1):
        with sqlite3.connect(db_path) as db:
            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor.execute(tips_query, [i, i])
            tips = cursor.fetchall()

        if not tips:
            break

        out_file = f"../out/tips_round_{i}.json"

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump(tips, f, indent=4)
