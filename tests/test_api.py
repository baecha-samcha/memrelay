from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from memory.store import Store
from demo.scenario import run_demo


def test_api_and_input_validation(store):
    with TestClient(create_app(store, Settings(llm_mode='mock'))) as client:
        assert client.get('/').status_code == 200
        assert client.get('/api/health').json()['storage'] == 'FalkorDB'
        response = client.post('/api/chat', json={'user':'alice','text':'Project Atlas uses Python'})
        assert response.status_code == 200
        assert client.get('/api/alice/snapshot').json()['memories']
        assert client.post('/api/chat', json={'user':'eve','text':'test'}).status_code == 422
        assert client.get('/api/eve/snapshot').status_code == 422
        assert client.post('/api/chat', json={'user':'alice','text':''}).status_code == 422


def test_real_database_unreachable_returns_503():
    s = Store('redis://127.0.0.1:1')
    with TestClient(create_app(s, Settings(llm_mode='mock'))) as client:
        for method, path, body in [('get','/api/health',None),('get','/api/alice/snapshot',None),('post','/api/chat',{'user':'alice','text':'Project Atlas uses Python'})]:
            response = getattr(client, method)(path, **({'json':body} if body else {}))
            assert response.status_code == 503
            assert response.json()['database'] == 'disconnected'


def test_demo_five_scenes(store):
    data = run_demo(store)
    try:
        assert {s['scene'] for s in data['transcript']} == {'Memory Creation','Memory Evolution','Agent Handoff','Persistence','User Isolation'}
        assert data['mode'] == 'mock'
        assert len(data['alice']['results']) == 1
        assert data['alice']['results'][0]['content'].startswith('- Project Atlas language: Rust')
        assert len(data['alice']['history']) == 1
        isolation = data['transcript'][-1]
        assert 'No supported' in isolation['empty_bob']['answer']
        assert 'Go' in isolation['response']['answer']
        assert store.memories('alice') == []
    finally:
        for user in ('alice','bob'):
            Store(prefix=data['graph_prefix'],client=store.db).graph(user).delete()
