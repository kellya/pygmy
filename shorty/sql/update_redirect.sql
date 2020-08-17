-- :name update_redirect
UPDATE redirect set url=:updateurl WHERE owner = :owner and id = :id
