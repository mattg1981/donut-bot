import os
import sqlite3
from datetime import datetime

def get_user_by_name(user):
    with sqlite3.connect(get_db_path(), isolation_level=None) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", [user])
        return cur.fetchone()


def get_users_by_name(users):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE username IN (%s)' %
                    ','.join('?' * len(users)), users)
        return cur.fetchall()


def add_unregistered_user(user, content_id):
    query = """
        INSERT INTO users (username, content_id, last_updated) 
        SELECT ?, ?, ?
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username=?) 
        RETURNING *
    """

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(query, [user, content_id, datetime.now(), user])
        return cur.fetchall()


def get_user_by_address(address):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE address=?", [address])
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


def insert_or_update_address(user, address, content_id):
    result = None
    user_address = get_user_by_name(user)

    exists = True
    if user_address is None:
        exists = False

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()

        if exists:
            cursor.execute(
                "UPDATE users SET address=?, content_id=?, last_updated=? WHERE username=? "
                "RETURNING *", [address, content_id, datetime.now(), user])
        else:
            cursor.execute(
                "INSERT INTO users (username, address, content_id, last_updated) VALUES (?,?,?,?) RETURNING *",
                [user, address, content_id, datetime.now()])

        return cursor.fetchone()


def process_earn2tip(user_address, parent_address, parent_name, amount, token, content_id, community):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("INSERT INTO earn2tip (from_address, to_address, to_user, amount, token, content_id, community, created_date) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *", [user_address, parent_address, parent_name, amount, token,
                                                              content_id, community, datetime.now()])
        return cur.fetchone()


def get_sub_status_for_current_round(subreddit):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(
            "select * from main.view_sub_distribution_tips where community = ?", [subreddit])
        return cur.fetchall()


def get_tips_sent_for_current_round_by_user(user):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(
            "SELECT from_address, token, count(tip.id) 'count', sum(amount) 'amount' FROM earn2tip tip 	inner join "
            "distribution_rounds dr WHERE tip.created_date BETWEEN dr.from_date and dr.to_date and "
            "from_address = (SELECT address from users where username = ?) GROUP BY from_address, token"
            , [user])
        return cur.fetchall()

def get_tips_received_for_current_round_by_user(user):
    sql = """
    SELECT to_address, token, count(tip.id) 'count', sum(amount) 'amount' 
    FROM earn2tip tip 	
    inner join 
        distribution_rounds dr WHERE tip.created_date BETWEEN dr.from_date and dr.to_date 
        and to_address = (SELECT address from users where username = ?) 
    GROUP BY to_address, token
    """

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [user])
        return cur.fetchall()


# def get_tip_status_for_current_round(user):
#     with sqlite3.connect(get_db_path()) as db:
#         db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
#         cur = db.cursor()
#         cur.execute("SELECT distribution_round from main.distribution_rounds where DATE() > from_date and "
#                     "DATE() < to_date")
#         dist_round = cur.fetchone()["distribution_round"]
#         cur.execute(
#             "SELECT from_address, token, count(id) 'count', sum(amount) 'amount' FROM earn2tip WHERE "
#             "distribution_round = ? and from_address = (SELECT address from registered_users where username = ?)"
#             "GROUP BY from_address, token", [dist_round, user])
#
#         return cur.fetchall()


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "../database/donut-bot.db")
    return os.path.normpath(db_path)
