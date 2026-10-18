from pathlib import Path
from typing import Literal
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.config import Settings
from memory.store import Store, DatabaseUnavailable, Conflict
from memory.visualization import read_graph, DemoGraphNotFound
from agents.coordinator import Coordinator
from agents.executor import Executor
from agents.llm import LLM
from demo.scenario import run_demo

STATIC = Path(__file__).parent / 'static'
User = Literal['alice', 'bob']


class Chat(BaseModel):
    user: User
    text: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default='demo', min_length=1, max_length=100)
    task_id: str | None = Field(default=None, min_length=1, max_length=100)


def create_app(store=None, settings=None):
    settings = settings or Settings()
    store = store or Store(settings.url, settings.prefix)
    api = FastAPI(title='MemRelay', version='0.1.0')
    api.state.store = store
    coordinator = Coordinator(store, LLM(settings))
    executor = Executor(store)

    @api.exception_handler(DatabaseUnavailable)
    def unavailable(request, exc):
        return JSONResponse(status_code=503, content={'detail': str(exc), 'database': 'disconnected'})

    @api.exception_handler(Conflict)
    def conflict(request, exc):
        return JSONResponse(status_code=409, content={'detail': str(exc)})

    @api.exception_handler(ValueError)
    def invalid(request, exc):
        return JSONResponse(status_code=422, content={'detail': str(exc)})

    @api.exception_handler(Exception)
    def unexpected(request, exc):
        # Do not expose provider credentials/URLs embedded in exception messages.
        logging.getLogger('memrelay').error('Request failed: %s', type(exc).__name__)
        return JSONResponse(status_code=502, content={'detail': 'Operation failed. Check configuration/provider availability. The graph may contain the recorded request.'})

    @api.get('/')
    def index():
        return FileResponse(STATIC / 'index.html')

    @api.get('/api/health')
    def health():
        return {**store.health(), 'llm_mode': settings.llm_mode}

    @api.get('/api/{user}/graph')
    def graph_view(user: User, demo_id: str | None = Query(default=None, pattern=r'^[0-9a-f]{10}$')):
        try:
            return read_graph(store, user, demo_id)
        except DemoGraphNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @api.get('/api/{user}/snapshot')
    def snapshot(user: User):
        return store.snapshot(user)

    @api.get('/api/{user}/memories')
    def memories(user: User, history: bool = False, subject: str = '', at: int | None = None):
        store.health()
        return store.memories(user, history, subject, at)

    @api.get('/api/{user}/tasks/{task_id}/events')
    def events(user: User, task_id: str):
        return [r[0] for r in store.run(user, 'events', id=task_id)]

    @api.post('/api/chat')
    def chat(body: Chat):
        return coordinator.chat(body.user, body.text, body.session_id, body.task_id)

    @api.post('/api/{user}/tasks/{task_id}/execute')
    def execute(user: User, task_id: str):
        return executor.execute(user, task_id)

    @api.post('/api/{user}/resume')
    def resume(user: User):
        return executor.resume(user)

    @api.post('/api/demo')
    def demo():
        store.health()
        return run_demo(store)

    api.mount('/static', StaticFiles(directory=STATIC), name='static')
    return api


app = create_app()
