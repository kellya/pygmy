-- :name get_record_by_id_with_owner :one
SELECT url FROM redirect WHERE id = :id and owner = :owner
