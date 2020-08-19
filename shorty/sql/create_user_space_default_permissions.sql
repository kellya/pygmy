-- :name create_user_space_default_permissions :insert 
INSERT INTO namespacePermission(owner, namespace) values (:owner, 2)
