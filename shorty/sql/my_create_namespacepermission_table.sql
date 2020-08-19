    -- :name my_create_namespacepermission_table
        CREATE TABLE namespacePermission(
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        owner INTEGER NOT NULL,
        namespace INTEGER NOT NULL,
        FOREIGN KEY(owner) REFERENCES owner(id),
        FOREIGN KEY(namespace) REFERENCES namespace(id)
        );
