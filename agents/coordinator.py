from agents.llm import LLM, explicit_correction, uncertain
from memory.store import uid


class Coordinator:
    """Interprets requests and durably assigns work; never executes tasks."""
    def __init__(self, store, llm=None):
        self.store = store
        self.llm = llm or LLM()

    def chat(self, user, text, session_id='demo', task_id=None):
        source = self.store.message(user, text, session_id)
        event = self.store.remember(user, source, 'episodic', text)
        intent = self.llm.interpret(text)
        used = []
        task = None
        if intent.action == 'remember':
            if intent.kind != 'episodic':
                memory = self.store.remember(
                    user, source, intent.kind, text, intent.subject, intent.predicate,
                    intent.object, explicit=explicit_correction(text),
                    task_type='project_summary' if intent.kind == 'procedural' else '',
                    instruction=intent.instruction, uncertain=uncertain(text),
                )
                used = [memory]
                answer = f"Stored {memory['kind']} memory ({memory['status']})."
            else:
                used = [event]
                answer = 'Recorded an episodic memory. Mock mode supports the documented Atlas scenario.'
        elif intent.action == 'history':
            used = self.store.memories(user, history=True, subject=intent.subject)
            changes = self.store.history(user, intent.subject)
            answer = '\n'.join(f"{c['before']} → {c['after']} [memory:{c['old_id']} → memory:{c['new_id']}]" for c in changes) or 'No explicit memory revisions in this user graph.'
        elif intent.action == 'task':
            task = self.store.create_task(user, task_id or uid(), text, source, intent.subject)
            used = self.store.memories(user, subject=intent.subject)
            self.store.run(user, 'task_context', id=task['id'], memory_ids=[m['id'] for m in used])
            answer = f"Coordinator → Executor: {task['id']} ({task['status']})."
        else:
            used = self.store.memories(user, subject=intent.subject)
            answer = self.llm.answer(used)
        response_id = self.store.message(user, answer, session_id, role='assistant')
        self.store.run(user, 'answer_evidence', id=response_id, memory_ids=[m['id'] for m in used])
        return {'answer': answer, 'message_id': response_id, 'evidence': used, 'task': task}
