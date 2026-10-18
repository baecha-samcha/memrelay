"""Bounded, read-only graph projection. No inferred nodes or relationships."""
import re
from redis.exceptions import RedisError
from memory.store import DatabaseUnavailable, QUERIES, now

MAX_NODES = 250
MAX_EDGES = 600


class DemoGraphNotFound(LookupError):
    pass


def read_graph(store, user, demo_id=None, node_limit=MAX_NODES, edge_limit=MAX_EDGES):
    if not 1 <= node_limit <= MAX_NODES or not 1 <= edge_limit <= MAX_EDGES:
        raise ValueError('Graph view limits out of range')
    if demo_id is not None and not re.fullmatch(r'[0-9a-f]{10}', demo_id):
        raise ValueError('Invalid demo ID')
    try:
        graph = store.graph(user)  # Validate the same user allowlist as the application.
        if demo_id is not None:
            graph = store.db.select_graph(f'{store.prefix}_demo_{demo_id}_{user}')
        # Do not initialize a user, create a graph, or call the Lite wrapper's
        # list_graphs helper (which swallows exceptions in the tested version).
        existing = store.db.connection.execute_command('GRAPH.LIST')
        existing = {name.decode() if isinstance(name, bytes) else name for name in existing}
        if graph.name not in existing:
            if demo_id is not None:
                raise DemoGraphNotFound('This demo graph does not exist.')
            rows, edge_rows = [], []
        else:
            rows = graph.ro_query((QUERIES / 'view_nodes.cypher').read_text(),
                                  {'limit': node_limit + 1}, timeout=5000).result_set
            ids = [row[0] for row in rows[:node_limit]]
            edge_rows = graph.ro_query((QUERIES / 'view_edges.cypher').read_text(),
                                       {'ids': ids, 'limit': edge_limit + 1}, timeout=5000).result_set if ids else []
        nodes = []
        for internal_id, labels, properties in rows[:node_limit]:
            props = dict(properties)
            node_type = next((label for label in labels if label in {
                'Memory', 'Message', 'Agent', 'Task', 'TaskResult', 'User', 'Session', 'Entity', 'TaskEvent'
            }), labels[0] if labels else 'Node')
            nodes.append({'data': {'id': f'n{internal_id}', 'type': node_type,
                                    'kind': props.get('kind', ''), 'status': props.get('status', ''),
                                    'labels': labels, 'properties': props}})
        edges = [{'data': {'id': f'e{eid}', 'source': f'n{source}', 'target': f'n{target}',
                           'type': relation, 'properties': dict(properties)}}
                 for eid, source, target, relation, properties in edge_rows[:edge_limit]]
        return {'user': user, 'demo_id': demo_id, 'graph_name': graph.name,
                'read_at': now(), 'read_only': True, 'nodes': nodes, 'edges': edges,
                'limits': {'nodes': node_limit, 'edges': edge_limit},
                'truncated': len(rows) > node_limit or len(edge_rows) > edge_limit,
                'nodes_truncated': len(rows) > node_limit, 'edges_truncated': len(edge_rows) > edge_limit}
    except RedisError as exc:
        raise DatabaseUnavailable('FalkorDB unavailable; graph view cleared.') from exc
