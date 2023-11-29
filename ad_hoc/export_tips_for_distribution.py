import csv
import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    DISTRIBUTION_ROUND = 130
    HARDCODED_BLOCK_FOR_OFFCHAIN = 30744221

    export_query = """
        SELECT 
           u1.username 'from_user'
          ,t.from_address
          ,u2.username 'to_user'
          ,t.to_address
          ,t.tx_hash
          ,t.block
          ,t.amount
          ,t.[timestamp]
          ,t.content_id
        FROM onchain_tip t
         left join users u1 on t.from_address = u1.address collate nocase
         left join users u2 on t.to_address = u2.address collate nocase
        
        UNION
        
        SELECT 
          COALESCE(e.from_user, u1.username) 'from_user'
          , e.from_address
          , e.to_user
          , u2.address 'to_address'
          , 'offchain:' || e.id 'tx_hash'
          , ? 'block'
          , e.amount
          , e.created_date 'timestamp'
          , e.parent_content_id 'content_id'
        from earn2tip e
          left join users u1 on e.from_address = u1.address collate nocase
          left join users u2 on e.to_user = u2.username collate nocase
        where e.created_date between 
          (select from_date from distribution_rounds where distribution_round = ?) and (select to_date from distribution_rounds where distribution_round = ?)
        
        order by timestamp desc
    """

    with sqlite3.connect(db_path) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute(export_query, [HARDCODED_BLOCK_FOR_OFFCHAIN, DISTRIBUTION_ROUND, DISTRIBUTION_ROUND])
        tips = cursor.fetchall()

    out_file = f"../out/export_tips_for_distribution_round_{DISTRIBUTION_ROUND}.csv"

    if os.path.exists(out_file):
        os.remove(out_file)

    # write new csv
    with open(out_file, 'w') as output_file:
        writer = csv.DictWriter(output_file, tips[0].keys(), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(tips)

