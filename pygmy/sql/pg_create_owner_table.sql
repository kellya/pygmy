    -- :name pg_create_owner_table
        CREATE TABLE owner(
        id INTEGER PRIMARY KEY SERIAL,
        username varchar(25) NOT NULL UNIQUE,
        "email" varchar(255)
        );
