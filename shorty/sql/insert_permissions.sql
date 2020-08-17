    -- :name insert_default_permissions :insert
        INSERT INTO permission (name,description) VALUES
        ('admin', 'Full administration of the site'),
        ('edit', 'default edit permissions that everyone gets'),
        ('keyword','Global keyword editing');
