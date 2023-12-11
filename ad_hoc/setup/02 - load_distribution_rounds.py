import json
import os.path
import sqlite3

from datetime import datetime, timedelta


def build_ethtrader_rounds():
    dist_round = 0
    start_date = None
    end_date = None

    while dist_round <= 300:
        if not dist_round:
            dist_round = 128
            start_date = datetime(2023, 8, 30, 0, 0, 0, 0)
            end_date = start_date + timedelta(days=28)
            end_date = end_date - timedelta(microseconds=1)
        else:
            start_date = end_date + timedelta(microseconds=1)
            end_date = start_date + timedelta(days=28)
            end_date = end_date - timedelta(microseconds=1)

        save_distribution_round(dist_round, start_date, end_date)
        dist_round += 1


def save_distribution_round(round, start_date, end_date):
    sql = """
    INSERT INTO distribution_rounds (from_date, to_date, community, distribution_round) VALUES (?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.execute(sql, [start_date, end_date, "ethtrader", round])


if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../../database/donut-bot.db")
    db_path = os.path.normpath(db_path)

    build_ethtrader_rounds()