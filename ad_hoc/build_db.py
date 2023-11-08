import json
import os.path
import urllib.request
import sqlite3

from datetime import datetime

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "../database/donut-bot.schema.db")
    db_path = os.path.normpath(db_path)

    sql = """
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
	
	CREATE VIEW view_sub_distribution_tips (community, token, distribution_round, tip_count, amount) as
    SELECT
      tip.community,
      tip.token,
      dr.distribution_round,
      count(tip.id) 'tip_count',
      sum(amount) 'amount'
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

        cursor.execute(sql)
