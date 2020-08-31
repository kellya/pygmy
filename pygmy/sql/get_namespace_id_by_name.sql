-- :name get_namespace_id_by_name :one
SELECT id from namespace where name=:name
