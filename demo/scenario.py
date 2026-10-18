"""Synthetic, repeatable scenario; no database reset or private data."""
from agents.coordinator import Coordinator
from agents.executor import Executor
from agents.llm import LLM
from app.config import Settings
from memory.store import Store, uid

SCENES = [
    ('Memory Creation', 'Project Atlas uses Python'),
    ('Memory Creation', 'For project summaries use bullet points and cite sources'),
    ('Memory Evolution', 'We switched Project Atlas to Rust'),
    ('Memory Evolution', 'What language does Project Atlas use?'),
    ('Memory Evolution', 'Show Project Atlas history'),
    ('Agent Handoff', 'Create a project summary'),
]


def run_demo(store):
    # Separate graph namespace preserves existing user data and makes reruns independent.
    prefix = store.prefix + '_demo_' + uid().replace('-', '')[:10]
    isolated = Store(prefix=prefix, client=store.db)
    llm = LLM(Settings(llm_mode='mock'))
    coordinator = Coordinator(isolated, llm)
    transcript = []
    for scene, text in SCENES:
        response = coordinator.chat('alice', text)
        item = {'scene': scene, 'input': text, 'response': response}
        if response['task']:
            item['execution'] = Executor(isolated).execute('alice', response['task']['id'])
        transcript.append(item)
    # Replace service and agent objects; database process deliberately stays running.
    restarted = Store(prefix=prefix, client=store.db)
    transcript.append({'scene': 'Persistence', 'scope': 'New Store/Coordinator objects; same DB client and running DB',
                       'response': Coordinator(restarted, llm).chat('alice', 'What language does Project Atlas use?')})
    empty_bob = Coordinator(restarted, llm).chat('bob', 'What language does Project Atlas use?')
    Coordinator(restarted, llm).chat('bob', 'Project Atlas uses Go')
    transcript.append({'scene': 'User Isolation', 'empty_bob': empty_bob,
                       'response': Coordinator(restarted, llm).chat('bob', 'What language does Project Atlas use?')})
    return {'graph_prefix': prefix, 'mode': 'mock', 'transcript': transcript,
            'alice': restarted.snapshot('alice'), 'bob': restarted.snapshot('bob')}


if __name__ == '__main__':
    import json
    s = Settings()
    print(json.dumps(run_demo(Store(s.url, s.prefix)), indent=2, ensure_ascii=False))
