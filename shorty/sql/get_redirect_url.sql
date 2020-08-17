-- :name get_redirect_url :one
SELECT url FROM redirect WHERE id = :id
