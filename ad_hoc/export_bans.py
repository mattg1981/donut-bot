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

    temp_ban_query = """
    SELECT 
       username,
       ban_date,
       community
    FROM bans
        where permanent = 0 
        and ban_date between (select from_date from distribution_rounds where distribution_round = ?) 
          and (select to_date from distribution_rounds where distribution_round = ?)    
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(rounds_query)
        round_result = cursor.fetchone()

    # build tips for last round and current round
    round_min = int(round_result["distribution_round"]) - 1
    round_max = int(round_result["distribution_round"])

    for i in range(round_min, round_max + 1):
        with sqlite3.connect(db_path) as db:
            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor.execute(temp_ban_query, [i, i])
            temp_bans = cursor.fetchall()

        out_file = f"../out/temp_bans_round_{i}.json"

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump(temp_bans, f, indent=4)

    perm_ban_query = """
        SELECT 
           username,
           ban_date,
           community
        FROM bans
            where permanent = 1 and is_overturned = 0 
        ORDER by 
            ban_date desc    
        """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(perm_ban_query)
        perm_bans = cursor.fetchall()

    perm_bans_out_file = f"../out/perm_bans.json"

    if os.path.exists(perm_bans_out_file):
        os.remove(perm_bans_out_file)

    with open(perm_bans_out_file, 'w') as f:
        json.dump(perm_bans, f, indent=4)
