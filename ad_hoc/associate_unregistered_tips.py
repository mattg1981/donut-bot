import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    query = """
    update earn2tip
    set to_address = (select address from users u where to_user = u.username COLLATE NOCASE)
    where to_address is NULL 
    """

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute(query)


