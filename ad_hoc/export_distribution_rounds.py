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
        where DATETIME() between from_date and to_date;
    """

    distribution_query = """
    SELECT 
       distribution_round,
       community,
       from_date,
       to_date
    FROM distribution_rounds
        where distribution_round = ?       
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(rounds_query)
        round_result = cursor.fetchone()

    round_min = int(round_result["distribution_round"]) - 1
    round_max = int(round_result["distribution_round"])

    for i in range(round_min, round_max + 1):
        with sqlite3.connect(db_path) as db:
            db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor.execute(distribution_query, [i])
            distribution_round = cursor.fetchall()

        if not distribution_round:
            continue

        out_file = f"../out/distribution_round_{i}.json"

        if os.path.exists(out_file):
            os.remove(out_file)

        with open(out_file, 'w') as f:
            json.dump(distribution_round, f, indent=4)
