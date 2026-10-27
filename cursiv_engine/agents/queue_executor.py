"""Deliberate, bounded local execution for deferred read-only research tasks."""
from types import SimpleNamespace

from . import offline_queue, workflow
from cursiv_engine.chat import request_budget
from cursiv_engine.core.command_api import TextResult, StreamResult


class Batch:
    def __init__(self, runtime, cfg):
        self.runtime, self.cfg = runtime, cfg
        self.owner = workflow.identity()
        self.budget = request_budget.Budget(0, seconds=1200)
        self.status = 'pending'

    def cancel(self):
        self.budget.cancelled.set()

    def check(self):
        self.budget.check()
        if workflow.identity() != self.owner:
            raise request_budget.Stopped('Person/workspace changed; deferred work stopped.')

    def execute(self, task):
        self.check()
        # No native commands, file writes, cloud cascade, tool execution or automatic memory recall.
        def local(messages, cfg, **kwargs):
            return self.runtime._call_ollama(messages, standard=True, **kwargs), ['Ollama (local)']
        adapter = SimpleNamespace(TextResult=TextResult, StreamResult=StreamResult,
                                  _cascade_stream=local, _call_ollama=self.runtime._call_ollama)
        prompt = task['prompt']
        text = prompt if prompt.startswith('@') or prompt.lower().startswith(('agents ask ', 'agent council ')) else 'agents ask ' + prompt
        result = workflow.command(adapter, text, dict(self.cfg, agent_local_only=True), [])
        run = getattr(result, 'run', None)
        if run is None:
            return offline_queue.Outcome('blocked', error=result.text)
        run.budget.cancelled = self.budget.cancelled
        run.budget.seconds = min(run.budget.seconds, self.budget.remaining_seconds)
        run.budget.valid = lambda: (self.budget.valid() and workflow.identity() == self.owner
                                   and offline_queue.active(task['id'], task['execution']))
        output = ''.join(result.generator)
        if run.status != 'succeeded':
            return offline_queue.Outcome(run.status if run.status in ('blocked', 'cancelled') else 'failed', error=run.final)
        if any('don\'t cover' in stage.text for stage in run.stages):
            return offline_queue.Outcome('blocked', error=output)
        return offline_queue.Outcome('succeeded', response=output)

    def stream(self):
        self.status = 'running'
        try:
            results = offline_queue.flush(self.execute, cancel_event=self.budget.cancelled)
            self.check()
            self.status = 'succeeded' if all(r['status'] == 'succeeded' for r in results) else 'blocked'
            yield ('No pending tasks.' if not results else '\n\n'.join(
                row['id'] + ' [' + row['status'] + ']\n' + (row.get('response') or row.get('error', '')) for row in results))
        except request_budget.Stopped:
            self.status = 'cancelled'
        except Exception as exc:
            self.status = 'failed'
            yield f'Deferred execution failed ({type(exc).__name__}: {exc}). Existing task history was retained.'


def command(runtime, cfg):
    batch = Batch(runtime, cfg)
    return runtime.StreamResult('Executing at most five local read-only tasks', batch.stream(), None, run=batch)
