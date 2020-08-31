-- :name update_last_used
UPDATE redirect SET lastUsed = :timestamp WHERE id = :recordid

