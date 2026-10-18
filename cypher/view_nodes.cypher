MATCH (n)
WITH n, CASE
 WHEN 'Agent' IN labels(n) THEN 0
 WHEN 'Memory' IN labels(n) AND n.kind <> 'episodic' THEN 1
 WHEN 'Task' IN labels(n) OR 'TaskResult' IN labels(n) THEN 2
 WHEN 'Memory' IN labels(n) THEN 3
 WHEN 'Message' IN labels(n) THEN 4
 ELSE 5 END AS priority
RETURN id(n), labels(n), properties(n)
ORDER BY priority, coalesce(n.created_at, 0) DESC, id(n)
LIMIT $limit
