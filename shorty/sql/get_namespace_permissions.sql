-- :name get_namespace_permissions :many
select namespace.id,namespace.name as namespace,namespace.description,namespace.icon from namespacePermission,owner,namespace where owner=owner.id and namespace=namespace.id and owner=:owner order by namespace;
