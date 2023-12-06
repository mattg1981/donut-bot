import os
import sqlite3
from datetime import datetime


def get_faucet_eligible(user):
    with sqlite3.connect(get_db_path()) as db:
        faucet_sql = """
            SELECT * 
            FROM view_faucet_can_request
            WHERE username=?;
        """
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(faucet_sql, [user])
        return cur.fetchone()


def add_faucet_history(user, address, direction, amount, tx_hash, block):
    with sqlite3.connect(get_db_path()) as db:
        insert_sql = """
            INSERT INTO faucet (username,
                       address,
                       direction,
                       amount,
                       tx_hash,
                       block,
                       created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING *;
        """
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(insert_sql, [user, address, direction, amount, tx_hash, block, datetime.now()])
        return cur.fetchone()


def get_user_by_name(user):
    with sqlite3.connect(get_db_path(), isolation_level=None) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE;", [user])
        return cur.fetchone()


def get_users_by_name(users):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT * FROM users WHERE username COLLATE NOCASE IN (%s);' %
                    ','.join('?' * len(users)), users)
        return cur.fetchall()

def get_user_by_address(address):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE address=? COLLATE NOCASE;", [address])
        return cur.fetchone()


def has_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('SELECT id FROM history WHERE content_id = ?;', [content_id])
        return cur.fetchone()


def set_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute('INSERT INTO history (content_id) VALUES(?) RETURNING *;', [content_id])
        return cur.fetchone()


def remove_processed_content(content_id):
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute("DELETE FROM history WHERE content_id = ?;", [content_id])


def insert_or_update_address(user, address, content_id):
    user_result = get_user_by_name(user)

    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = db.cursor()

        if user_result:
            sql = """
                UPDATE users 
                SET address=?, content_id=?, last_updated=? 
                WHERE username=? COLLATE NOCASE
                RETURNING *;
            """
            cursor.execute(sql, [address, content_id, datetime.now(), user])
        else:
            sql = """
                INSERT INTO users (username, address, content_id, last_updated) 
                VALUES (?,?,?,?) 
                RETURNING *;
            """
            cursor.execute(sql,[user, address, content_id, datetime.now()])

        return cursor.fetchone()


def process_earn2tips(tips):
    sql = """
    INSERT INTO earn2tip (from_user, from_address, to_user, to_address, amount, token, content_id, 
                          parent_content_id, submission_content_id, community, created_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ;
    """

    history_sql = "INSERT INTO history (content_id) VALUES(?) RETURNING *;"
    content_id = tips[0].content_id

    created_date = datetime.now()
    data = []

    for tip in tips:
        tip.created_date = created_date
        data.append((tip.sender_name, tip.sender_address, tip.recipient_name, tip.recipient_address,  tip.amount, tip.token,
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
    SELECT from_user, token, count(tip.id) 'count', sum(amount) 'amount' 
    FROM earn2tip tip 	
      inner join distribution_rounds dr 
    WHERE tip.created_date BETWEEN dr.from_date and dr.to_date 
      and from_user = ? COLLATE NOCASE
      and DATE() between dr.from_date and dr.to_date
    GROUP BY from_user, token
    """
    with sqlite3.connect(get_db_path()) as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = db.cursor()
        cur.execute(sql, [user])
        return cur.fetchall()


def get_tips_received_for_current_round_by_user(user):
    sql = """
    SELECT to_user, token, count(tip.id) 'count', sum(amount) 'amount' 
    FROM earn2tip tip 	
      inner join distribution_rounds dr 
    WHERE tip.created_date BETWEEN dr.from_date and dr.to_date 
        and to_user = ? COLLATE NOCASE
        and DATE() between dr.from_date and dr.to_date
    GROUP BY to_user, token
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
        and u.username = ? COLLATE NOCASE
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
