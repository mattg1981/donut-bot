import os
import sqlite3


def get_address_for_user(author):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        c = db.cursor()
        c.execute("SELECT username, address FROM registered_users WHERE username=?", [author])
        return c.fetchone()


def get_address_for_users(authors):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()
        cursor.execute('SELECT username, address FROM registered_users WHERE username IN (%s)' %
                       ','.join('?' * len(authors)), authors)
        return cursor.fetchall()


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "../database/donut-bot.db")
    return os.path.normpath(db_path)
