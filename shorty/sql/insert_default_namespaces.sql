-- :name insert_default_namespaces
INSERT INTO namespace(name,description,icon)
VALUES
('global', 'default - shortcuts that start from the root of the domain','fa-globe'),
('user', 'default - shortcuts that begin with /~<username>','fa-user')
