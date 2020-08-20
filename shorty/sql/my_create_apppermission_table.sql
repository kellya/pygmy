-- :name my_create_apppermission_table
    CREATE TABLE appPermission (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    owner INTEGER,
    permission INTEGER,
    FOREIGN KEY(owner) REFERENCES owner(id),
    FOREIGN KEY(permission) REFERENCES permission(id)
    );
