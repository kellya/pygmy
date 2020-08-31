-- :name get_user_permissions :many
select permission.name from permission, appPermission where permission = permission.id and owner=:owner
