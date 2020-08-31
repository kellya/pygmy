    -- :name my_create_redirect_table
        CREATE TABLE redirect(
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        owner INTEGER NOT NULL,
        url TEXT NOT NULL,
        createTime INTEGER,
        lastUsed INTEGER,
        hit INTEGER DEFAULT 0,
        namespace INTEGER NOT NULL,
        keyword varchar(25),
        FOREIGN KEY(owner) REFERENCES owner(id),
        FOREIGN KEY(namespace) REFERENCES namespace(id)
        );
