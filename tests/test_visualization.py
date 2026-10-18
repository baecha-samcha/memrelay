from fastapi.testclient import TestClient
import pytest
from app.config import Settings
from app.main import create_app
from memory.store import Store
from memory.visualization import read_graph, DemoGraphNotFound
from tests.test_memory import coordinator
from agents.executor import Executor
from demo.scenario import run_demo


def seed(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    c.chat('alice', 'For project summaries use bullet points and cite sources')
    c.chat('alice', 'We switched Project Atlas to Rust')
    task = c.chat('alice', 'Create a project summary')['task']
    Executor(store).execute('alice', task['id'])


def test_graph_exports_only_actual_nodes_and_relationships(store):
    seed(store)
    view = read_graph(store, 'alice')
    actual_nodes = store.query('alice', 'MATCH (n) RETURN id(n), properties(n)')
    actual_edges = store.query('alice', 'MATCH (a)-[r]->(b) RETURN id(r), id(a), id(b), type(r), properties(r)')
    exported_nodes = {n['data']['id']: n['data'] for n in view['nodes']}
    assert set(exported_nodes) == {f'n{row[0]}' for row in actual_nodes}
    for identity, properties in actual_nodes:
        assert exported_nodes[f'n{identity}']['properties'] == properties
    exported_edges = {e['data']['id']: e['data'] for e in view['edges']}
    assert set(exported_edges) == {f'e{row[0]}' for row in actual_edges}
    for identity, source, target, relation, properties in actual_edges:
        assert exported_edges[f'e{identity}'] == {'id':f'e{identity}', 'source':f'n{source}',
                                                 'target':f'n{target}', 'type':relation, 'properties':properties}
    assert {'Memory','Message','Agent','Task','TaskResult'} <= {n['type'] for n in exported_nodes.values()}
    assert {'episodic','semantic','procedural'} <= {n['kind'] for n in exported_nodes.values()}
    assert {'SUPPORTS','SUPERSEDES','USES_MEMORY','HANDED_OFF_TO'} <= {e['type'] for e in exported_edges.values()}
    revision = next(e for e in exported_edges.values() if e['type'] == 'SUPERSEDES')
    assert exported_nodes[revision['source']]['properties']['object'] == 'Rust'
    assert exported_nodes[revision['target']]['properties']['object'] == 'Python'
    assert view['read_only'] and not view['truncated']


def test_graph_read_does_not_create_empty_user_graph(store):
    before = store.db.connection.execute_command('GRAPH.LIST')
    view = read_graph(store, 'bob')
    assert not view['nodes'] and not view['edges']
    assert store.db.connection.execute_command('GRAPH.LIST') == before


def test_graph_export_uses_ro_query_and_preserves_graph(store, monkeypatch):
    seed(store)
    before = store.snapshot('alice')
    graph = store.graph('alice')
    calls = []
    original = graph.ro_query
    def read_only(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)
    def no_write(*args, **kwargs):
        raise AssertionError('Visualization attempted a write query')
    monkeypatch.setattr(graph, 'ro_query', read_only)
    monkeypatch.setattr(graph, 'query', no_write)
    monkeypatch.setattr(store, 'graph', lambda user: graph)
    read_graph(store, 'alice')
    assert len(calls) == 2
    monkeypatch.undo()
    assert store.snapshot('alice') == before


def test_visualization_user_and_demo_graph_isolation(store):
    coordinator(store).chat('alice', 'Project Atlas uses Java')
    data = run_demo(store)
    demo_id = data['graph_prefix'].rsplit('_demo_', 1)[1]
    try:
        current = read_graph(store, 'alice')
        alice = read_graph(store, 'alice', demo_id)
        bob = read_graph(store, 'bob', demo_id)
        def languages(view):
            return {n['data']['properties']['object'] for n in view['nodes']
                    if n['data']['type']=='Memory' and n['data']['kind']=='semantic'
                    and n['data']['status']=='active'}
        assert languages(current) == {'Java'}
        assert languages(alice) == {'Rust'}
        assert languages(bob) == {'Go'}
        assert alice['graph_name'] != bob['graph_name'] != current['graph_name']
        assert any(e['data']['type']=='SUPERSEDES' for e in alice['edges'])
        assert not any(e['data']['type']=='SUPERSEDES' for e in bob['edges'])
    finally:
        for user in ('alice','bob'):
            Store(prefix=data['graph_prefix'],client=store.db).graph(user).delete()


def test_graph_caps_and_edges_have_loaded_endpoints(store):
    store.query('alice', '''UNWIND range(0, 260) AS i
        CREATE (:Memory {id: toString(i), kind: 'semantic', status: 'active'})''')
    view = read_graph(store, 'alice')
    assert len(view['nodes']) == 250 and view['nodes_truncated']
    assert view['truncated']
    seed(store)
    bounded = read_graph(store, 'alice', node_limit=20, edge_limit=2)
    ids = {n['data']['id'] for n in bounded['nodes']}
    assert len(bounded['edges']) <= 2
    assert all(e['data']['source'] in ids and e['data']['target'] in ids for e in bounded['edges'])


def test_graph_edge_cap_reports_partial_view(store):
    seed(store)
    result = read_graph(store, 'alice', edge_limit=2)
    assert len(result['edges']) == 2 and result['edges_truncated']
    assert result['truncated']
    assert result['edges'][0]['data']['type'] == 'SUPERSEDES'


def test_graph_api_validation_and_empty_demo(store):
    with TestClient(create_app(store, Settings(llm_mode='mock'))) as client:
        assert client.get('/api/alice/graph').status_code == 200
        assert client.get('/api/eve/graph').status_code == 422
        assert client.get('/api/alice/graph?demo_id=../../other').status_code == 422
        assert client.get('/api/alice/graph?demo_id=aaaaaaaaaa').status_code == 404
    with pytest.raises(ValueError):
        read_graph(store, 'alice', 'invalid')
    with pytest.raises(DemoGraphNotFound):
        read_graph(store, 'alice', 'aaaaaaaaaa')


def test_graph_api_database_failure_has_no_cached_elements():
    with TestClient(create_app(Store('redis://127.0.0.1:1'), Settings(llm_mode='mock'))) as client:
        result = client.get('/api/alice/graph')
        assert result.status_code == 503
        assert result.json()['database'] == 'disconnected'
        assert 'nodes' not in result.json() and 'edges' not in result.json()
