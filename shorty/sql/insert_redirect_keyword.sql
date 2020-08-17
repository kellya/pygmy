-- :name insert_redirect_keyword :insert
INSERT INTO redirect (url, owner, createTime, namespace, keyword)
VALUES (
    :url,
    :owner,
    :createTime,
    :namespace,
    :keyword
)
