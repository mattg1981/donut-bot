-- drop the `special_membership` table
drop table special_membership;

-- begin add column 'community' to the 'flair' table
PRAGMA foreign_keys = 0;

CREATE TABLE sqlitestudio_temp_table AS SELECT *
                                          FROM flair;

DROP TABLE flair;

CREATE TABLE flair (
    id           INTEGER  NOT NULL
                          PRIMARY KEY AUTOINCREMENT,
    user_id      INT      NOT NULL,
    hash         INTEGER,
    last_update  DATETIME NOT NULL,
    created_at   DATETIME NOT NULL
                          DEFAULT CURRENT_TIMESTAMP,
    community    TEXT     COLLATE NOCASE,
    custom_flair TEXT     COLLATE NOCASE
);

INSERT INTO flair (
                      id,
                      user_id,
                      hash,
                      last_update,
                      created_at,
                      custom_flair
                  )
                  SELECT id,
                         user_id,
                         hash,
                         last_update,
                         created_at,
                         custom_flair
                    FROM sqlitestudio_temp_table;

DROP TABLE sqlitestudio_temp_table;

CREATE UNIQUE INDEX flair_user_id_idx ON flair (
    user_id
);

PRAGMA foreign_keys = 1;

-- end

-------------------------------------------- set value
update flair set community = 'ethtrader';

-------------------------------------------- make `community` not null
PRAGMA foreign_keys = 0;

CREATE TABLE sqlitestudio_temp_table AS SELECT *
                                          FROM flair;

DROP TABLE flair;

CREATE TABLE flair (
    id           INTEGER  NOT NULL
                          PRIMARY KEY AUTOINCREMENT,
    user_id      INT      NOT NULL,
    hash         INTEGER,
    last_update  DATETIME NOT NULL,
    created_at   DATETIME NOT NULL
                          DEFAULT CURRENT_TIMESTAMP,
    community    TEXT     COLLATE NOCASE
                          NOT NULL,
    custom_flair TEXT     COLLATE NOCASE
);

INSERT INTO flair (
                      id,
                      user_id,
                      hash,
                      last_update,
                      created_at,
                      community,
                      custom_flair
                  )
                  SELECT id,
                         user_id,
                         hash,
                         last_update,
                         created_at,
                         community,
                         custom_flair
                    FROM sqlitestudio_temp_table;

DROP TABLE sqlitestudio_temp_table;

CREATE UNIQUE INDEX flair_user_id_idx ON flair (
    user_id
);

PRAGMA foreign_keys = 1;