-- :name get_redirect_keyword :one
SELECT url FROM redirect WHERE keyword = :keyword and namespace=1
