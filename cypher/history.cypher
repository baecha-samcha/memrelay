MATCH (n:Memory)-[:SUPERSEDES]->(o:Memory)
WHERE $subject = '' OR n.subject = $subject
OPTIONAL MATCH (s:Message)-[:SUPPORTS]->(n)
RETURN {new_id: n.id, old_id: o.id, before: o.content, after: n.content,
 changed_at: n.created_at, source: properties(s), relationship: 'SUPERSEDES'}
ORDER BY n.created_at
