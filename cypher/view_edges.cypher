MATCH (a)-[r]->(b)
WHERE id(a) IN $ids AND id(b) IN $ids
WITH a, r, b, CASE
 WHEN type(r) = 'SUPERSEDES' THEN 0
 WHEN type(r) = 'HANDED_OFF_TO' THEN 1
 WHEN type(r) = 'SUPPORTS' OR type(r) = 'USES_MEMORY' THEN 2
 ELSE 3 END AS priority
RETURN id(r), id(a), id(b), type(r), properties(r)
ORDER BY priority, id(r)
LIMIT $limit
