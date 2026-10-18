MATCH (m:Memory)
WHERE ($subject = '' OR m.subject = $subject)
AND (($at = 0 AND ($history OR m.status = 'active'))
 OR ($at > 0 AND m.status <> 'disputed' AND m.valid_from <= $at
 AND (m.valid_to = 0 OR $at < m.valid_to)))
OPTIONAL MATCH (s:Message)-[:SUPPORTS]->(m)
WHERE $at = 0 OR s.created_at <= $at
WITH m, collect(properties(s)) AS sources
RETURN {id: m.id, kind: m.kind, content: m.content, subject: m.subject,
 predicate: m.predicate, object: m.object, status: m.status,
 created_at: m.created_at, updated_at: m.updated_at, valid_from: m.valid_from,
 valid_to: m.valid_to, task_type: m.task_type, instruction: m.instruction,
 sources: sources}
ORDER BY m.created_at, m.id
