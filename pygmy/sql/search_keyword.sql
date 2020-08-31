-- :name search_keyword :one

SELECT count(*) as count FROM redirect where owner=:owner and namespace=:namespace and keyword=:keyword
