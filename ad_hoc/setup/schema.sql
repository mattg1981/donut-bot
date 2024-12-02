CREATE TABLE `distribution_rounds` (
		`id` integer not null primary key autoincrement,
		`from_date` datetime not null,
		`to_date` datetime not null,
		`community` nvarchar2 not null,
		`distribution_round` integer not null
	);
CREATE TABLE _litestream_seq (id INTEGER PRIMARY KEY, seq INTEGER);
CREATE TABLE _litestream_lock (id INTEGER);
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
            , chain_id integer, weight REAL);
CREATE TABLE flair (
    id          INTEGER  NOT NULL
                         PRIMARY KEY AUTOINCREMENT,
    user_id     INT      NOT NULL,
    hash        INTEGER,
    last_update DATETIME NOT NULL,
    created_at  DATETIME NOT NULL
                         DEFAULT CURRENT_TIMESTAMP
, custom_flair TEXT collate NOCASE);
CREATE TABLE users (
    id           INTEGER   NOT NULL
                           PRIMARY KEY AUTOINCREMENT,
    username     NVARCHAR2 NOT NULL
                           COLLATE NOCASE,
    address      NVARCHAR2 COLLATE NOCASE,
    content_id   NVARCHAR2,
    last_updated DATETIME  NOT NULL
                           DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE faucet (
        id           INTEGER         NOT NULL
                                     PRIMARY KEY AUTOINCREMENT,
        username     NVARCHAR2       NOT NULL
                                     COLLATE NOCASE,
        address      NVARCHAR2       NOT NULL
                                     COLLATE NOCASE,
        direction    NVARCHAR2       NOT NULL
                                     DEFAULT 'OUTBOUND'
                                     COLLATE NOCASE,
        amount       DECIMAL (10, 5) NOT NULL,
        tx_hash      NVARCHAR2       NOT NULL
                                     COLLATE BINARY,
        block        INTEGER         NOT NULL,
        notified_date DATETIME,
        created_date DATETIME        NOT NULL
                                     DEFAULT CURRENT_TIMESTAMP
    );
CREATE TABLE funded_account (
    id           INTEGER         NOT NULL
                                 PRIMARY KEY AUTOINCREMENT,
    from_user    NVARCHAR2       COLLATE NOCASE,
    from_address NVARCHAR2       NOT NULL
                                 COLLATE NOCASE,
    amount       DECIMAL (10, 5) NOT NULL,
    token        NVARCHAR2       NOT NULL,
    block_number INTEGER         NOT NULL,
    tx_hash      NVARCHAR2       NOT NULL,
    tx_timestamp VARCHAR (255)   NOT NULL,
    processed_at DATETIME,
    created_at   DATETIME        NOT NULL
                                 DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE earn2tip (
    id                    INTEGER         NOT NULL
                                          PRIMARY KEY AUTOINCREMENT,
    from_user             NVARCHAR2       COLLATE NOCASE,
    to_user               NVARCHAR2       COLLATE NOCASE,
    amount                DECIMAL (10, 5) NOT NULL,
    token                 NVARCHAR2       NOT NULL
                                          COLLATE NOCASE,
    content_id            NVARCHAR2,
    parent_content_id     NVARCHAR2,
    submission_content_id NVARCHAR2,
    community             NVARCHAR2       NOT NULL
                                          COLLATE NOCASE,
    created_date          DATETIME        NOT NULL
                                          DEFAULT CURRENT_TIMESTAMP,
    processed_date        DATETIME
, weight REAL);
CREATE TABLE history (
    id         INTEGER   NOT NULL
                         PRIMARY KEY AUTOINCREMENT,
    content_id NVARCHAR2 NOT NULL,
    command NVARCHAR2 NOT NULL,
    created_at DATETIME  NOT NULL
                         DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE moderators (
    id             INTEGER   PRIMARY KEY AUTOINCREMENT
                             NOT NULL,
    name           NVARCHAR2 NOT NULL
                             COLLATE NOCASE,
    date_assigned  DATETIME  NOT NULL,
    community      NVARCHAR2 NOT NULL
                             COLLATE NOCASE,
    bonus_eligible BOOLEAN   DEFAULT (1),
    is_active      BOOLEAN   NOT NULL
                             DEFAULT (1),
    last_update    DATETIME  NOT NULL
                             DEFAULT (CURRENT_TIMESTAMP),
    created_date   DATETIME  DEFAULT (CURRENT_TIMESTAMP) 
                             NOT NULL
);
CREATE TABLE special_membership (
    id           INTEGER   PRIMARY KEY AUTOINCREMENT
                           NOT NULL,
    user         NVARCHAR2 COLLATE NOCASE,
    address      NVARCHAR2 NOT NULL
                           COLLATE NOCASE,
    start_date   DATETIME  NOT NULL,
    end_date     DATETIME  NOT NULL,
    community    NVARCHAR2 NOT NULL
                           COLLATE NOCASE,
    network      NVARCHAR2 COLLATE NOCASE
                           NOT NULL,
    created_date DATETIME  DEFAULT (CURRENT_TIMESTAMP) 
                           NOT NULL
);
CREATE TABLE bans (
    id            INTEGER   NOT NULL
                            PRIMARY KEY AUTOINCREMENT,
    username      NVARCHAR2 NOT NULL
                            COLLATE NOCASE,
    note          NVARCHAR2 NOT NULL,
    ban_date      DATETIME  NOT NULL,
    is_overturned BOOLEAN   DEFAULT (0) 
                            NOT NULL,
    permanent     BOOLEAN   NOT NULL,
    days_left     INT,
    community     NVARCHAR2 NOT NULL
                            COLLATE BINARY,
    last_updated  DATETIME,
    created_at    DATETIME  NOT NULL
                            DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE post (
                id             INTEGER   NOT NULL
                                         PRIMARY KEY AUTOINCREMENT,
                submission_id  NVARCHAR2 NOT NULL
                                         COLLATE NOCASE,
                tip_comment_id NVARCHAR2 COLLATE NOCASE,
                author         NVARCHAR2 COLLATE NOCASE,
                is_daily       BOOLEAN   DEFAULT (0),
                created_date   DATETIME  NOT NULL
                                         DEFAULT CURRENT_TIMESTAMP
            , community TEXT collate NOCASE);
CREATE TABLE liquidity_positions
(
    id     integer not null
        constraint liquidity_positions_pk
            primary key autoincrement,
    nft_id integer not null
);
CREATE TABLE potd
(
    id           INTEGER                            not null
        primary key autoincrement,
    post_id      TEXT                               not null,
    redditor     TEXT collate NOCASE                not null,
    weight       INTEGER  default 0,
    created_date DATETIME default CURRENT_TIMESTAMP not null,
    community    TEXT collate NOCASE
);
CREATE UNIQUE INDEX onchain_tip_tx_hash_idx on onchain_tip(tx_hash);
CREATE UNIQUE INDEX flair_user_id_idx on flair(user_id);
CREATE UNIQUE INDEX idx_special_membership_address_start_date ON special_membership (
    address,
    start_date
);
CREATE UNIQUE INDEX bans_username_bandate ON bans (
    username,
    ban_date
);
CREATE UNIQUE INDEX idx_unique_post_submission_id ON post (
                    submission_id
                );
CREATE UNIQUE INDEX chain_id__tx_hash ON onchain_tip (
                chain_id,
                tx_hash
            );
CREATE UNIQUE INDEX potd_redditor_created_date_uindex
    on potd (redditor, created_date);
CREATE VIEW view_sub_distribution_tips (
    community,
    token,
    distribution_round,
    tip_count,
    amount,
    average_tip_amount
  ) as
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
  dr.distribution_round
/* view_sub_distribution_tips(community,token,distribution_round,tip_count,amount,average_tip_amount) */;
CREATE VIEW view_faucet_can_request AS
    SELECT u.username,
           u.address,
           s.created_date
      FROM users u
           LEFT JOIN
           (
               SELECT username,
                      max(created_date) created_date
                 FROM faucet
                WHERE direction = 'OUTBOUND'
                GROUP BY username
           )
           s ON u.username = s.username
     WHERE s.created_date IS NULL OR 
           s.created_date <= Datetime('now', '-28 days', 'localtime')
/* view_faucet_can_request(username,address,created_date) */;
CREATE TABLE membership_season
(
    id               integer                        not null
        primary key autoincrement,
    season_number    integer                        not null,
    contract_address TEXT collate NOCASE,
    event_block      integer,
    start_date       TEXT collate NOCASE            not null,
    end_date         TEXT collate NOCASE,
    community        TEXT collate NOCASE            not null,
    created_date     TEXT default CURRENT_TIMESTAMP not null
);
CREATE VIEW view_flair_can_update as
SELECT u.username,
           u.address,
           f.hash,
           f.last_update,
           f.custom_flair,
           f.last_update IS NULL OR f.last_update <= Datetime('now', '-60 minutes', 'localtime') as eligible
      FROM users u
           LEFT JOIN
           flair f ON u.id = f.user_id
/* view_flair_can_update(username,address,hash,last_update,custom_flair,eligible) */;
