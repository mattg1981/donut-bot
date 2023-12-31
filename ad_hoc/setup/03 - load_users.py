import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    user_json = json.load(urllib.request.urlopen("https://ethtrader.github.io/donut.distribution/users.json"))

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()

        for user in user_json:
            print(f'user: {user["username"]} -- address: {user["address"]}')
            cursor.execute("INSERT INTO users (username, address, last_updated) VALUES (?, ?, ?)",
                           (user["username"], user["address"], datetime.now()))

        cursor.execute("INSERT INTO users (username, address, last_updated) VALUES (?, ?, ?)",
                       ['donut-bot', '0xa8C8c9e18C763805c91bcB720B2320aDe16a0BBf', datetime.now()])

