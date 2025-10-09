import csv
import os
import sqlite3

if __name__ == '__main__':
    # locate database
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    with sqlite3.connect(db_path) as db:
        query = """
        SELECT
           u1.username from_user,
           from_address,
           u2.username to_user,
           to_address,
           tx_hash,
           block,
           amount,
           weight,
           token,
           t.content_id,
           timestamp
          FROM onchain_tip t
            left join users u1 on t.from_address = u1.address
            left join users u2 on t.to_address = u2.address
          ORDER BY block desc;

        """
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(query)
        tips = cursor.fetchall()

    out_file = "../out/onchain_tips.csv"

    if os.path.exists(out_file):
        os.remove(out_file)

    # write new csv (if there are tips)
    if tips:
        with open(out_file, 'w') as output_file:
            writer = csv.DictWriter(output_file, tips[0].keys(), extrasaction='ignore')
            writer.writeheader()
            writer.writerows(tips)