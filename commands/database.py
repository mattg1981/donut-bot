import os
import sqlite3


def get_address_for_user(author):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT username, address FROM registered_users WHERE username=?", [author])
        return cur.fetchone()


def get_addresses_for_users(authors):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT username, address FROM registered_users WHERE username IN (%s)' %
                       ','.join('?' * len(authors)), authors)
        return cur.fetchall()


def process_earn2tip(user_address, author_address, amount, token, content_id, community):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("INSERT INTO earn2tip (from_address, to_address, amount, token, content_id, community) "
                  "VALUES (?, ?, ?, ?, ?, ?) RETURNING *", [user_address, author_address, amount, token,
                                                            content_id, community])
        return cur.fetchone()

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
