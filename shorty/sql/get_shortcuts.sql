-- :name get_shortcuts :many
SELECT * FROM redirect WHERE owner = :owner
