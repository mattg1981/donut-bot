import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.schema.db")
    db_path = os.path.normpath(db_path)

    tables_and_views = """
    CREATE TABLE `distribution_rounds` (
		`id` integer not null primary key autoincrement,
		`from_date` datetime not null,
		`to_date` datetime not null,
		`community` nvarchar2 not null,
		`distribution_round` integer not null
	);
	
	CREATE TABLE `earn2tip` (
		`id` integer not null primary key autoincrement,
		`from_address` NVARCHAR2 not null,
		`to_address` NVARCHAR2 null,
		`to_user` NVARCHAR2 null,
		`amount` DECIMAL(10,5) not null,
		`token` NVARCHAR2 not null,
		`content_id` NVARCHAR2 null,
		`parent_content_id` NVARCHAR2 null,
		`submission_content_id` NVARCHAR2 null,
		`community` nvarchar2 not null,
		`created_date` datetime not null default CURRENT_TIMESTAMP,
		`processed_date` datetime null
	);
	
	CREATE TABLE
	`faucet` (
		`id` integer not null primary key autoincrement,
		`address` NVARCHAR2 not null, 
		`direction` NVARCHAR2 not null default 'OUTBOUND',
		`created_date` datetime not null default CURRENT_TIMESTAMP
	);
	
	CREATE TABLE `history` (
		`id` integer not null primary key autoincrement,
		`content_id` nvarchar2 not null,
		`created_at` datetime not null default CURRENT_TIMESTAMP
	);
	
	CREATE TABLE `users` (
		`id` integer not null primary key autoincrement,
		`username` NVARCHAR2 not null,
		`address` NVARCHAR2 null,
		`content_id` NVARCHAR2 null,
		`last_updated` datetime not null default CURRENT_TIMESTAMP
	);
	
	CREATE TABLE `funded_account` (
        `id` integer not null primary key autoincrement,
        `from_address` NVARCHAR2 not null,
        `blockchain_amount` FLOAT not null,
        `amount` FLOAT not null,
        `token` NVARCHAR2 not null,
        `block_number` INTEGER not null,
        `tx_hash` NVARCHAR2 not null,
        `tx_timestamp` varchar(255) not null,
        `processed_at` DATETIME null,
        `created_at` datetime not null default CURRENT_TIMESTAMP
    );
    
    CREATE TABLE `settings` (
        `id` integer not null primary key autoincrement,
        `setting` NVARCHAR2 not null,
        `value` NVARCHAR2 null,
        `updated_at` DATETIME not null default CURRENT_TIMESTAMP,
        `created_at` datetime not null default CURRENT_TIMESTAMP
      );
      
    CREATE TABLE onchain_tip (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        from_address NVARCHAR2 NOT NULL COLLATE NOCASE,
        to_address NVARCHAR2 NOT NULL COLLATE NOCASE,
        tx_hash NVARCHAR2 NOT NULL COLLATE NOCASE,
        block BIGINT,
        amount DECIMAL(10, 5) NOT NULL,
        token NVARCHAR2 NOT NULL,
        content_id NVARCHAR2,
        timestamp DATETIME NOT NULL,
        created_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
        
    CREATE TABLE `multisig_tips` (
        `id` integer not null primary key autoincrement,
        `from_address` NVARCHAR2 not null,
        `to_address` NVARCHAR2 null,
        `author` NVARCHAR2 null,
        `tx_hash` NVARCHAR2 not null,
        `block_number` BIGINT not null,
        `amount` DECIMAL not null,
        `token` NVARCHAR2 not null,
        `timestamp` DATETIME not null,
        `content_id` NVARCHAR2 not null,
        `distributed_at` DATETIME null,
        `created_at` datetime not null default CURRENT_TIMESTAMP
    );
	
	CREATE VIEW view_sub_distribution_tips (community, token, distribution_round, tip_count, amount, average_tip_amount) as
    SELECT
      tip.community,
      tip.token,
      dr.distribution_round,
      count(tip.id) 'tip_count',
      sum(amount) 'amount',
      avg(amount) 'average_tip_amount'
    FROM
      earn2tip tip
      inner join distribution_rounds dr
    WHERE
      (
        tip.created_date > dr.from_date
        and tip.created_date < dr.to_date
      )
    GROUP BY
      tip.community,
      tip.token,
      dr.distribution_round;
    """

    with sqlite3.connect(db_path) as db:
        cursor = db.cursor()
        cursor.executescript(tables_and_views)

        # add required data now
        cursor.execute("insert into settings (setting, value, updated_at, created_at) values (?,?,?,?)",
                       ['funded_account_last_block', 30952176, datetime.now(), datetime.now()])

        cursor.execute("insert into settings (setting, value, updated_at, created_at) values (?,?,?,?)",
                       ['funded_account_last_runtime', datetime.now(), datetime.now(), datetime.now()])

