    -- :name my_create_owner_table
        CREATE TABLE owner(
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        username varchar(25) NOT NULL UNIQUE,
        email varchar(255)
        );
