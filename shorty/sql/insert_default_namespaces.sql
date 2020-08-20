-- :name insert_default_namespaces
INSERT INTO namespace(name,description)
VALUES
('global', 'default - shortcuts that start from the root of the domain'),
('user', 'default - shortcuts that begin with /~<username>')
