-- :name get_namespace_redirect :one
SELECT url FROM redirect where namespace=:namespace and keyword=:keyword
