-- :name get_user_namespace_redirect :one
SELECT url FROM redirect where namespace=2 and owner=:owner and keyword=:keyword
