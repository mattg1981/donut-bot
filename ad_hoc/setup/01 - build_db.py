import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

###
#   DEPRECATED - PLEASE USE SCHEMA.SQL TO BUILD THE DATABASE
###

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.schema.db")
    db_path = os.path.normpath(db_path)

    tables_and_views = """
#     CREATE TABLE distribution_rounds (
#         id                 INTEGER   NOT NULL
#                                      PRIMARY KEY AUTOINCREMENT,
#         from_date          DATETIME  NOT NULL,
#         to_date            DATETIME  NOT NULL,
#         community          NVARCHAR2 NOT NULL
#                                      COLLATE NOCASE,
#         distribution_round INTEGER   NOT NULL
#     );
# 	
# 	CREATE TABLE earn2tip (
#         id                    INTEGER         NOT NULL
#                                               PRIMARY KEY AUTOINCREMENT,
#         from_user             NVARCHAR2       COLLATE NOCASE,
#         to_user               NVARCHAR2       COLLATE NOCASE,
#         amount                DECIMAL (10, 5) NOT NULL,
#         weight                REAL,
#         token                 NVARCHAR2       NOT NULL
#                                               COLLATE NOCASE,
#         content_id            NVARCHAR2,
#         parent_content_id     NVARCHAR2,
#         submission_content_id NVARCHAR2,
#         community             NVARCHAR2       NOT NULL
#                                               COLLATE NOCASE,
#         created_date          DATETIME        NOT NULL
#                                               DEFAULT CURRENT_TIMESTAMP,
#         processed_date        DATETIME
#     );
# 	
# 	CREATE TABLE faucet (
#         id           INTEGER         NOT NULL
#                                      PRIMARY KEY AUTOINCREMENT,
#         username     NVARCHAR2       NOT NULL
#                                      COLLATE NOCASE,
#         address      NVARCHAR2       NOT NULL
#                                      COLLATE NOCASE,
#         direction    NVARCHAR2       NOT NULL
#                                      DEFAULT 'OUTBOUND'
#                                      COLLATE NOCASE,
#         amount       DECIMAL (10, 5) NOT NULL,
#         tx_hash      NVARCHAR2       NOT NULL
#                                      COLLATE BINARY,
#         block        INTEGER         NOT NULL,
#         notified_date DATETIME,
#         created_date DATETIME        NOT NULL
#                                      DEFAULT CURRENT_TIMESTAMP
#     );
# 
# 	CREATE TABLE history (
#     id         INTEGER   NOT NULL
#                          PRIMARY KEY AUTOINCREMENT,
#     content_id NVARCHAR2 NOT NULL,
#     command NVARCHAR2 NOT NULL,
#     created_at DATETIME  NOT NULL
#                          DEFAULT CURRENT_TIMESTAMP
# );
# 
# CREATE TABLE moderators (
#     id             INTEGER   PRIMARY KEY AUTOINCREMENT
#                              NOT NULL,
#     name           NVARCHAR2 NOT NULL
#                              COLLATE NOCASE,
#     date_assigned  DATETIME  NOT NULL,
#     community      NVARCHAR2 NOT NULL
#                              COLLATE NOCASE,
#     bonus_eligible BOOLEAN   DEFAULT (1),
#     is_active      BOOLEAN   NOT NULL
#                              DEFAULT (1),
#     last_update    DATETIME  NOT NULL
#                              DEFAULT (CURRENT_TIMESTAMP),
#     created_date   DATETIME  DEFAULT (CURRENT_TIMESTAMP) 
#                              NOT NULL
# );
# 
# CREATE TABLE special_membership (
#     id           INTEGER   PRIMARY KEY AUTOINCREMENT
#                            NOT NULL,
#     user         NVARCHAR2 COLLATE NOCASE,
#     address      NVARCHAR2 NOT NULL
#                            COLLATE NOCASE,
#     start_date   DATETIME  NOT NULL,
#     end_date     DATETIME  NOT NULL,
#     community    NVARCHAR2 NOT NULL
#                            COLLATE NOCASE,
#     network      NVARCHAR2 COLLATE NOCASE
#                            NOT NULL,
#     created_date DATETIME  DEFAULT (CURRENT_TIMESTAMP) 
#                            NOT NULL
# );
# 
# CREATE UNIQUE INDEX idx_special_membership_address_start_date ON special_membership (
#     address,
#     start_date
# );
# 
# 
# 
# 	
# 	
# 	CREATE TABLE users (
#     id           INTEGER   NOT NULL
#                            PRIMARY KEY AUTOINCREMENT,
#     username     NVARCHAR2 NOT NULL
#                            COLLATE NOCASE,
#     address      NVARCHAR2 COLLATE NOCASE,
#     content_id   NVARCHAR2,
#     last_updated DATETIME  NOT NULL
#                            DEFAULT CURRENT_TIMESTAMP
#     );
# 	
# 	
#     CREATE TABLE funded_account (
#         id                INTEGER       NOT NULL
#                                         PRIMARY KEY AUTOINCREMENT,
#         from_user         NVARCHAR2     COLLATE NOCASE,
#         from_address      NVARCHAR2     NOT NULL
#                                         COLLATE NOCASE,
#         blockchain_amount FLOAT         NOT NULL,
#         amount            FLOAT         NOT NULL,
#         token             NVARCHAR2     NOT NULL,
#         block_number      INTEGER       NOT NULL,
#         tx_hash           NVARCHAR2     NOT NULL,
#         tx_timestamp      VARCHAR (255) NOT NULL,
#         processed_at      DATETIME,
#         created_at        DATETIME      NOT NULL
#                                         DEFAULT CURRENT_TIMESTAMP
#     );
#     
#     CREATE TABLE `settings` (
#         `id` integer not null primary key autoincrement,
#         `setting` NVARCHAR2 not null,
#         `value` NVARCHAR2 null,
#         `updated_at` DATETIME not null default CURRENT_TIMESTAMP,
#         `created_at` datetime not null default CURRENT_TIMESTAMP
#       );
#       
#     CREATE TABLE onchain_tip (
#         id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#         from_address NVARCHAR2 NOT NULL COLLATE NOCASE,
#         to_address NVARCHAR2 NOT NULL COLLATE NOCASE,
#         tx_hash NVARCHAR2 NOT NULL COLLATE NOCASE,
#         block BIGINT,
#         amount DECIMAL(10, 5) NOT NULL,
#         token NVARCHAR2 NOT NULL,
#         content_id NVARCHAR2,
#         timestamp DATETIME NOT NULL,
#         created_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
#     );
#         
#     CREATE TABLE `multisig_tips` (
#         `id` integer not null primary key autoincrement,
#         `from_address` NVARCHAR2 not null,
#         `to_address` NVARCHAR2 null,
#         `author` NVARCHAR2 null,
#         `tx_hash` NVARCHAR2 not null,
#         `block_number` BIGINT not null,
#         `amount` DECIMAL not null,
#         `token` NVARCHAR2 not null,
#         `timestamp` DATETIME not null,
#         `content_id` NVARCHAR2 not null,
#         `distributed_at` DATETIME null,
#         `created_at` datetime not null default CURRENT_TIMESTAMP
#     );
# 	
# 	CREATE VIEW view_sub_distribution_tips (community, token, distribution_round, tip_count, amount, average_tip_amount) as
#     SELECT
#       tip.community,
#       tip.token,
#       dr.distribution_round,
#       count(tip.id) 'tip_count',
#       sum(amount) 'amount',
#       avg(amount) 'average_tip_amount'
#     FROM
#       earn2tip tip
#       inner join distribution_rounds dr
#     WHERE
#       (
#         tip.created_date > dr.from_date
#         and tip.created_date < dr.to_date
#       )
#     GROUP BY
#       tip.community,
#       tip.token,
#       dr.distribution_round;
#       
#     CREATE VIEW view_flair_can_update (
#         username,
#         address,
#         hash,
#         last_update
#     )
#     AS
#         SELECT u.username,
#                u.address,
#                f.hash,
#                f.last_update
#           FROM users u
#                LEFT JOIN
#                flair f ON u.id = f.user_id
#          WHERE f.last_update IS NULL OR 
#                f.last_update <= Datetime('now', '-20 minutes', 'localtime');
# 
# CREATE VIEW view_faucet_can_request AS
#     SELECT u.username,
#            u.address,
#            s.created_date
#       FROM users u
#            LEFT JOIN
#            (
#                SELECT username,
#                       max(created_date) created_date
#                  FROM faucet
#                 WHERE direction = 'OUTBOUND'
#                 GROUP BY username
#            )
#            s ON u.username = s.username
#      WHERE s.created_date IS NULL OR 
#            s.created_date <= Datetime('now', '-28 days', 'localtime');

    """

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.executescript(tables_and_views)

        # add required data now
        cursor.execute("insert into settings (setting, value, updated_at, created_at) values (?,?,?,?)",
                       ['funded_account_last_block', 30952176, datetime.now(), datetime.now()])

        cursor.execute("insert into settings (setting, value, updated_at, created_at) values (?,?,?,?)",
                       ['funded_account_last_runtime', datetime.now(), datetime.now(), datetime.now()])
