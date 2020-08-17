-- :name update_redirect_hits

UPDATE redirect SET hit = hit + 1, lastUsed = :lastUsed  WHERE id = :recordid
