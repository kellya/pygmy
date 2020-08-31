-- :name get_record_by_keyword :one
SELECT id FROM redirect WHERE keyword = :keyword and namespace=:namespace
