-- :name create_owner_default_permissions
INSERT INTO appPermission(owner, permission) values (:owner, 2)
