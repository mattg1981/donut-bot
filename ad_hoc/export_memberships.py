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

    membership_query = """
    SELECT user,
       address,
       start_date,
       end_date,
       community,
       network
    FROM special_membership
    WHERE end_date >= (
                           SELECT to_date
                             FROM distribution_rounds
                            WHERE distribution_round = ?
                       )
    AND 
           user IS NOT NULL;    
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
            cursor.execute(membership_query, [i])
            mods = cursor.fetchall()

        if not mods:
            continue

        out_file = f"../out/memberships_{i}.json"

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump(mods, f, indent=4)
