import os
import sqlite3
from datetime import datetime


def get_address_for_user(author):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT username, address FROM registered_users WHERE username=?", [author])
        return cur.fetchone()


def has_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT id FROM history WHERE content_id = ?', [content_id])
        return cur.fetchone()


def set_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('INSERT INTO history (content_id) VALUES(?) RETURNING *', [content_id])
        return cur.fetchone()


def remove_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("DELETE FROM history WHERE content_id = ?", [content_id])


def get_addresses_for_users(authors):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT username, address FROM registered_users WHERE username IN (%s)' %
                    ','.join('?' * len(authors)), authors)
        return cur.fetchall()


def insert_or_update_address(user, address, content_id):
    result = None
    user_address = get_address_for_user(user)

    exists = True
    if user_address is None:
        exists = False

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()

        if exists:
            cursor.execute(
                "UPDATE registered_users SET address=?, content_id=?, last_updated=? WHERE username=? "
                "RETURNING *", [address, content_id, datetime.now(), user])
        else:
            cursor.execute(
                "INSERT INTO registered_users (username, address, content_id) VALUES (?,?,?) RETURNING *",
                [user, address, content_id])

        return cursor.fetchone()


def process_earn2tip(user_address, author_address, amount, token, content_id, community):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("INSERT INTO earn2tip (from_address, to_address, amount, token, content_id, community) "
                    "VALUES (?, ?, ?, ?, ?, ?) RETURNING *", [user_address, author_address, amount, token,
                                                              content_id, community])
        return cur.fetchone()

def get_tip_status_for_current_round_new(user):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(
            "SELECT from_address, token, count(tip.id) 'count', sum(amount) 'amount' FROM earn2tip tip 	inner join "
            "distribution_rounds dr WHERE tip.created_at > dr.from_date and tip.created_at < dr.to_date and "
            "from_address = (SELECT address from registered_users where username = ?) GROUP BY from_address, token"
            , [user])
        return cur.fetchall()

def get_tip_status_for_current_round(user):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT distribution_round from main.distribution_rounds where DATE() > from_date and "
                    "DATE() < to_date")
        dist_round = cur.fetchone()["distribution_round"]
        cur.execute(
            "SELECT from_address, token, count(id) 'count', sum(amount) 'amount' FROM earn2tip WHERE "
            "distribution_round = ? and from_address = (SELECT address from registered_users where username = ?)"
            "GROUP BY from_address, token", [dist_round, user])

        return cur.fetchall()


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "../database/donut-bot.db")
    return os.path.normpath(db_path)
