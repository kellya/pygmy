-- :name insert_redirect :insert
INSERT INTO redirect (url, owner, createTime, namespace)
VALUES (
    :url,
    :owner,
    :createTime,
    :namespace
)
