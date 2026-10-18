from concurrent.futures import ThreadPoolExecutor
import time
from memory.store import Store
from agents.coordinator import Coordinator
from agents.llm import LLM
from app.config import Settings


def coordinator(store):
    return Coordinator(store, LLM(Settings(llm_mode='mock')))


def test_three_kinds_and_sources(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    c.chat('alice', 'For project summaries use bullet points and cite sources')
    memories = store.memories('alice')
    assert {m['kind'] for m in memories} == {'semantic', 'episodic', 'procedural'}
    assert all(m['sources'] and m['sources'][0]['role'] == 'user' for m in memories)
    assert all(m['created_at'] and m['updated_at'] for m in memories)


def test_revision_current_history_and_time(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    past = store.memories('alice', subject='Project Atlas')[0]['valid_from']
    time.sleep(.01)
    c.chat('alice', 'We switched Project Atlas from Python to Rust')
    current = store.memories('alice', subject='Project Atlas')
    assert len(current) == 1 and current[0]['object'] == 'Rust'
    history = store.history('alice')
    assert len(history) == 1
    assert history[0]['source']['content'] == 'We switched Project Atlas from Python to Rust'
    assert history[0]['old_id'] != history[0]['new_id']
    old = store.memories('alice', subject='Project Atlas', at=past)
    assert old[0]['object'] == 'Python'
    assert old[0]['sources'][0]['content'] == 'Project Atlas uses Python'
    assert old[0]['valid_to'] > past
    assert 'Rust' in c.chat('alice', 'What language does Atlas use?')['answer']


def test_contradiction_and_uncertainty_not_overwritten(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    c.chat('alice', 'Project Atlas uses Go')
    c.chat('alice', 'Maybe we switched Project Atlas to Rust')
    assert store.memories('alice', subject='Project Atlas')[0]['object'] == 'Python'
    assert len([m for m in store.memories('alice', True) if m['status'] == 'disputed']) == 2
    assert store.history('alice') == []


def test_uncertain_initial_fact_is_not_active(store):
    coordinator(store).chat('alice', 'Maybe Project Atlas uses Rust')
    assert store.memories('alice', subject='Project Atlas') == []


def test_users_are_separate_graphs(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    assert 'No supported' in c.chat('bob', 'What language does Atlas use?')['answer']
    c.chat('bob', 'Project Atlas uses Go')
    assert store.graph('alice').name != store.graph('bob').name
    assert 'Python' in c.chat('alice', 'What language does Atlas use?')['answer']
    bob = c.chat('bob', 'What language does Atlas use?')
    assert 'Go' in bob['answer'] and 'Python' not in bob['answer']
    assert not ({m['id'] for m in bob['evidence']} & {m['id'] for m in store.memories('alice')})


def test_new_store_has_persistent_memory(store):
    coordinator(store).chat('alice', 'Project Atlas uses Rust')
    restarted = Store(prefix=store.prefix, client=store.db)
    assert restarted.memories('alice', subject='Project Atlas')[0]['object'] == 'Rust'


def test_parallel_memory_writes(store):
    store.initialize('alice')
    def write(i):
        source = store.message('alice', f'event {i}', f'session-{i}')
        return store.remember('alice', source, 'episodic', f'event {i}')['id']
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(write, range(16)))
    assert len(set(ids)) == 16
    assert len(store.memories('alice')) == 16


def test_parallel_corrections_one_active_slot(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    def write(language):
        return c.chat('alice', f'We switched Project Atlas to {language}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(write, ['Rust', 'Go']))
    assert len(store.memories('alice', subject='Project Atlas')) == 1
    assert len(store.history('alice')) == 2


def test_parameters_are_not_cypher(store):
    text = "event ' }) MATCH (n) DETACH DELETE n //"
    source = store.message('alice', text)
    store.remember('alice', source, 'episodic', text)
    assert store.memories('alice')[0]['content'] == text


def test_provenance_persists_on_answer(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    answer = c.chat('alice', 'What language does Atlas use?')
    rows = store.query('alice', 'MATCH (:Message {id: $id})-[:USES_MEMORY]->(m:Memory)<-[:SUPPORTS]-(s:Message) RETURN m.id, s.content', id=answer['message_id'])
    assert rows[0][0] == answer['evidence'][0]['id']
    assert rows[0][1] == 'Project Atlas uses Python'


def test_negation_does_not_authorize_replacement(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    c.chat('alice', "We haven't switched Project Atlas to Rust")
    assert store.memories('alice', subject='Project Atlas')[0]['object'] == 'Python'
    assert store.history('alice') == []


def test_corroborating_fact_adds_source(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    c.chat('alice', 'Project Atlas currently uses Python')
    active = store.memories('alice', subject='Project Atlas')
    assert len(active) == 1 and len(active[0]['sources']) == 2


def test_historical_evidence_excludes_future_corroboration(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    past = store.memories('alice', subject='Project Atlas')[0]['valid_from']
    time.sleep(.01)
    c.chat('alice', 'Project Atlas currently uses Python')
    assert len(store.memories('alice', subject='Project Atlas')[0]['sources']) == 2
    old = store.memories('alice', subject='Project Atlas', at=past)
    assert len(old[0]['sources']) == 1
    assert old[0]['sources'][0]['content'] == 'Project Atlas uses Python'


def test_same_object_uncertainty_or_denial_is_not_support(store):
    c = coordinator(store)
    c.chat('alice', 'Project Atlas uses Python')
    for text in ('Maybe Project Atlas uses Python', 'Project Atlas does not use Python'):
        result = c.chat('alice', text)
        assert result['evidence'][0]['status'] == 'disputed'
    active = store.memories('alice', subject='Project Atlas')
    assert len(active) == 1 and active[0]['object'] == 'Python'
    assert len(active[0]['sources']) == 1
    assert len([m for m in store.memories('alice', True) if m['status'] == 'disputed']) == 2
    assert store.history('alice') == []
