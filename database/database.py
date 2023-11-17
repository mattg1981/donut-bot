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


def process_earn2tips(tips):
    sql = """
    INSERT INTO earn2tip (from_address, to_address, to_user, amount, token, content_id, 
                          parent_content_id, submission_content_id, community, created_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) 
    """

    history_sql = "INSERT INTO history (content_id) VALUES(?) RETURNING *;"
    content_id = tips[0].content_id

    created_date = datetime.now()
    data = []

    for tip in tips:
        tip.created_date = created_date
        data.append((tip.sender_address, tip.recipient_address, tip.recipient_name, tip.amount, tip.token,
                     tip.content_id, tip.parent_content_id, tip.submission_content_id, tip.community, created_date))

    with sqlite3.connect(get_db_path()) as db:
        db.isolation_level = None
        cur = db.cursor()

        cur.execute("begin")
        try:
            cur.executemany(sql, data)
            cur.execute(history_sql, [content_id])
            cur.execute("commit")
            return True
        except sqlite3.Error as e:
            cur.execute("rollback")
            return False


def get_sub_status_for_current_round(subreddit):
    sql = """
    select
        *
    from
        main.view_sub_distribution_tips
    where
        community = ?
        and distribution_round = (
            select
                distribution_round
            from
                distribution_rounds
            where
                DATE() between from_date
                and to_date
        )
    """
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [subreddit])
        return cur.fetchall()


def get_tips_sent_for_current_round_by_user(user):
    sql = """
    SELECT from_address, token, count(tip.id) 'count', sum(amount) 'amount' 
    FROM earn2tip tip 	
    inner join distribution_rounds dr 
    WHERE tip.created_date BETWEEN dr.from_date and dr.to_date 
      and from_address = (SELECT address from users where username = ?) 
      and DATE() between dr.from_date and dr.to_date
    GROUP BY from_address, token
    """
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [user])
        return cur.fetchall()


def get_tips_received_for_current_round_by_user(user):
    sql = """
    SELECT to_address, token, count(tip.id) 'count', sum(amount) 'amount' 
    FROM earn2tip tip 	
    inner join distribution_rounds dr 
    WHERE tip.created_date BETWEEN dr.from_date and dr.to_date 
        and to_address = (SELECT address from users where username = ?) 
        and DATE() between dr.from_date and dr.to_date
    GROUP BY to_address, token
    """

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [user])
        return cur.fetchall()

def get_funded_for_current_round_by_user(user):
    sql = """
    SELECT u.username, token, sum(amount) 'amount' 
    FROM funded_account fund 	
      inner join users u on fund.from_address = u.address COLLATE NOCASE
      inner join distribution_rounds dr
    WHERE fund.processed_at BETWEEN dr.from_date and dr.to_date 
        and u.username = ?
        and DATE() between dr.from_date and dr.to_date
    GROUP BY u.username, token
    """

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [user])
        return cur.fetchall()


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "donut-bot.db")
    return os.path.normpath(db_path)
