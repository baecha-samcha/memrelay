MERGE (e:Entity {id: $slot}) ON CREATE SET e.version = 0, e.name = $subject
RETURN e.version
