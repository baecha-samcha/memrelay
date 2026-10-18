"""Submission audit against a real local FalkorDB, with an actual TCP cut.

Run separately from pytest: python scripts/verify_graph_dependency.py [--browser]
Only synthetic audit_<uuid> graphs are created; existing user graphs are untouched.
No credentials, source contents, or database dumps are printed.
"""
import argparse
import json
from pathlib import Path
import select
import socket
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import uvicorn
from app.config import Settings
from app.main import create_app
from memory.store import Store


class Gate:
    def __init__(self):
        self.enabled = True
        self.stopped = False
        self.connections = set()
        self.lock = threading.Lock()
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen()
        self.listener.settimeout(.2)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.accept, daemon=True)
        self.thread.start()

    def accept(self):
        while not self.stopped:
            try:
                downstream, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            if not self.enabled:
                downstream.close()
                continue
            try:
                upstream = socket.create_connection(('127.0.0.1', 6379), timeout=3)
            except OSError:
                downstream.close()
                continue
            with self.lock:
                self.connections.update((downstream, upstream))
            threading.Thread(target=self.forward, args=(downstream, upstream), daemon=True).start()

    def forward(self, downstream, upstream):
        try:
            while self.enabled and not self.stopped:
                readable, _, _ = select.select([downstream, upstream], [], [], .2)
                for source in readable:
                    payload = source.recv(65536)
                    if not payload:
                        return
                    (upstream if source is downstream else downstream).sendall(payload)
        except (OSError, ValueError):
            pass
        finally:
            with self.lock:
                self.connections.discard(downstream)
                self.connections.discard(upstream)
            downstream.close()
            upstream.close()

    def cut(self):
        self.enabled = False
        with self.lock:
            for connection in list(self.connections):
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()

    def restore(self):
        self.enabled = True

    def close(self):
        self.cut()
        self.stopped = True
        self.listener.close()
        self.thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', action='store_true')
    args = parser.parse_args()
    gate = Gate()
    prefix = 'audit_' + uuid.uuid4().hex[:12]
    store = Store(f'redis://127.0.0.1:{gate.port}', prefix)
    api_socket = socket.socket()
    api_socket.bind(('127.0.0.1', 0))
    port = api_socket.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(store, Settings(llm_mode='mock')), log_level='warning'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [api_socket]}, daemon=True)
    thread.start()
    browser = None
    playwright = None
    records = []

    def record(name, **data):
        row = {'check': name, 'status': 'PASS', **data}
        records.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)

    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=45) as client:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(.05)
            assert server.started

            def chat(text, task_id=None):
                result = client.post('/api/chat', json={'user': 'alice', 'text': text, 'task_id': task_id})
                assert result.status_code == 200, result.status_code
                return result.json()

            assert client.get('/api/health').status_code == 200
            chat('Project Atlas uses Python')
            first = chat('What language does Project Atlas use?')
            assert 'Python' in first['answer'] and first['evidence'][0]['sources']
            chat('For project summaries use bullet points and cite sources')
            chat('We switched Project Atlas to Rust')
            current = chat('What language does Project Atlas use?')
            assert 'Rust' in current['answer'] and 'Python' not in current['answer']
            rows = store.query('alice', '''MATCH (n:Memory)-[:SUPERSEDES]->(o:Memory)
                MATCH (s:Message)-[:SUPPORTS]->(n)
                RETURN n.object, n.status, o.object, o.status, n.id, o.id, s.id''')
            assert rows[0][:4] == ['Rust', 'active', 'Python', 'superseded']
            record('graph_revision_changes_answer', before='Python', after='Rust',
                   graph_prefix=prefix, path='new:Rust -SUPERSEDES-> old:Python',
                   new_memory_id=rows[0][4], old_memory_id=rows[0][5], source_id=rows[0][6])
            chat('Create a project summary', 'audit-task')
            execution = client.post('/api/alice/tasks/audit-task/execute').json()
            assert execution['result']['content'].startswith('- Project Atlas language: Rust')
            paths = store.query('alice', '''MATCH (t:Task {id: $id})-[:PRODUCED]->(r:TaskResult)
                MATCH (r)-[:USES_MEMORY]->(m:Memory)<-[:SUPPORTS]-(s:Message)
                RETURN t.status, m.kind, m.object, m.instruction, m.id, s.id''', id='audit-task')
            assert {r[1] for r in paths} == {'semantic', 'procedural'}
            assert all(r[0] == 'completed' for r in paths)
            events = client.get('/api/alice/tasks/audit-task/events').json()
            assert [e['status'] for e in events] == ['pending', 'running', 'completed']
            record('executor_uses_graph_fact_and_procedure', task_id='audit-task',
                   memory_kinds=sorted({r[1] for r in paths}),
                   transitions=[e['status'] for e in events], result_prefix='- Project Atlas language: Rust')
            # Opposite procedure experiment: no rule in Bob's independent graph.
            client.post('/api/chat', json={'user': 'bob', 'text': 'Project Atlas uses Go'}).raise_for_status()
            b = client.post('/api/chat', json={'user': 'bob', 'text': 'Create a project summary', 'task_id': 'bob-task'}).json()
            bresult = client.post('/api/bob/tasks/bob-task/execute').json()['result']['content']
            assert b['task']['status'] == 'pending' and bresult.startswith('Project Atlas language: Go')
            assert not bresult.startswith('- ')
            record('procedure_changes_real_output', alice='bullets + Rust', bob='no bullets + Go')
            chat('Create a project summary', 'audit-pending')
            before = store.query('alice', 'MATCH (m:Message) RETURN count(m)')[0][0]
            if args.browser:
                from playwright.sync_api import sync_playwright, expect
                playwright = sync_playwright().start()
                expect.set_options(timeout=30000)
                browser = playwright.chromium.launch(args=['--disable-dev-shm-usage'])
                page = browser.new_page(viewport={'width': 1100, 'height': 800})
                page.goto(f'http://127.0.0.1:{port}', wait_until='domcontentloaded', timeout=60000)
                expect(page.locator('#connection')).to_have_text('● FalkorDB connected')
                expect(page.locator('#user')).to_be_enabled()
            gate.cut()  # Closes existing TCP sockets and refuses forwarded traffic.
            checks = [('GET', '/api/health', None), ('GET', '/api/alice/snapshot', None),
                      ('GET', '/api/alice/memories', None),
                      ('POST', '/api/chat', {'user': 'alice', 'text': 'What language does Project Atlas use?'}),
                      ('POST', '/api/alice/tasks/audit-pending/execute', {}),
                      ('POST', '/api/alice/resume', {}), ('POST', '/api/demo', {})]
            statuses = {}
            for method, path, body in checks:
                result = client.request(method, path, **({'json': body} if body is not None else {}))
                assert result.status_code == 503, (path, result.status_code)
                assert result.json()['database'] == 'disconnected'
                statuses[path] = result.status_code
            assert client.get('/').status_code == 200
            if args.browser:
                page.click('#refresh')
                expect(page.locator('#connection')).to_have_text('● FalkorDB disconnected')
                expect(page.locator('#error')).to_be_visible()
            record('actual_tcp_disconnect', http_statuses=statuses, static_ui=200,
                   browser_indicator='verified' if args.browser else 'NOT TESTED')
            gate.restore()
            assert client.get('/api/health').status_code == 200
            assert store.query('alice', 'MATCH (m:Message) RETURN count(m)')[0][0] == before
            assert 'Rust' in chat('What language does Project Atlas use?')['answer']
            pending = store.task('alice', 'audit-pending')
            assert pending['status'] == 'pending' and pending['attempts'] == 0
            assert client.post('/api/alice/tasks/audit-pending/execute').json()['result']['status'] == 'completed'
            if args.browser:
                page.click('#refresh')
                expect(page.locator('#connection')).to_have_text('● FalkorDB connected')
                expect(page.locator('#user')).to_be_enabled()
            record('connection_restored_same_app', old_memory='Rust', offline_writes=0,
                   recovered_task='completed', browser_indicator='verified' if args.browser else 'NOT TESTED')
    finally:
        gate.restore()  # Restore first even if an assertion fails.
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
        server.should_exit = True
        thread.join(timeout=10)
        gate.close()
    print(json.dumps({'status': 'PASS', 'checks': len(records), 'graph_prefix': prefix,
                      'scope': 'Real local FalkorDB unchanged; only audit app TCP transport was cut.'}), flush=True)


if __name__ == '__main__':
    main()
