-- :name get_redirect_keyword_ns :one
SELECT url FROM redirect WHERE keyword = :keyword and namespace=:namespace
