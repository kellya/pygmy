-- :name get_shortcuts :many
SELECT redirect.*, namespace.name as namespace_name, namespace.icon as icon FROM redirect, namespace WHERE owner = :owner and namespace=namespace.id
ORDER BY namespace_name
