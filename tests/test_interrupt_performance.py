"""Measured synthetic UI/helper overhead; never a model-speed benchmark."""
import ast
import json
from pathlib import Path
import statistics
import time
import tracemalloc

from test_chat_feedback import panel
from cursiv_engine.chat import continuity


def test_measure_interrupt_and_resume_overhead(panel, monkeypatch, tmp_path):
    import chat_panel
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: False)
    # Freeze the existing U114 Stop function by extracting only this reviewed
    # method, not importing/executing an older application checkout.
    text = (Path(__file__).parent/'fixtures/u114_stop.py.txt').read_text(encoding='utf-8')
    tree = ast.parse(text)
    method = next(n for cls in tree.body if isinstance(cls, ast.ClassDef) and cls.name == 'ChatPanel'
                  for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_stop_generation')
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), '<frozen-u114-stop>', 'exec'), namespace)
    panel._begin_turn('Synthetic baseline task')
    started = time.perf_counter_ns()
    namespace['_stop_generation'](panel)
    baseline_ms = (time.perf_counter_ns()-started)/1e6
    baseline_released = not panel._streaming and panel._send_btn.isEnabled()
    panel._on_cancelled()
    timings, checkpoint_ns, prepare_ns = [], [], []
    original = continuity.checkpoint
    def measured(*a, **k):
        start = time.perf_counter_ns()
        result = original(*a, **k)
        checkpoint_ns.append(time.perf_counter_ns()-start)
        return result
    monkeypatch.setattr(continuity, 'checkpoint', measured)
    tracemalloc.start()
    for i in range(50):
        panel._begin_turn('Explain iron oxidation mechanisms')
        panel._reply_is_chat = True
        panel._on_chunk('Iron oxidation can occur through several electrochemical pathways. ' * 8)
        start = time.perf_counter_ns()
        panel._stop_generation()
        timings.append((time.perf_counter_ns()-start)/1e6)
        assert not panel._streaming and panel._send_btn.isEnabled()
        row = panel._paused()[0]
        start = time.perf_counter_ns()
        packet = continuity.prepare(row)
        prepare_ns.append(time.perf_counter_ns()-start)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    row = panel._paused()[0]
    metadata = json.dumps(row['interruption'], ensure_ascii=False).encode()
    before = len(json.dumps({k:v for k,v in row.items() if k != 'interruption'}, ensure_ascii=False).encode())
    after = len(json.dumps(row, ensure_ascii=False).encode())
    file = tmp_path/'synthetic-checkpoint.json'
    file.write_bytes(json.dumps(row, ensure_ascii=False).encode())
    report = dict(scope='50 synthetic offscreen UI interruptions; autosave off; tracemalloc on; no inference; not real-provider latency',
        baseline=dict(commit='7d7e1e3', stop_handler_ms=baseline_ms, input_released_on_return=baseline_released,
                      note='U114 waits for worker completion; no invented stop-to-release duration'),
        after=dict(iterations=50, stop_handler_median_ms=statistics.median(timings), stop_handler_max_ms=max(timings),
                   stop_handler_p95_ms=sorted(timings)[47], input_released_on_return=True,
                   checkpoint_median_ms=statistics.median(checkpoint_ns)/1e6,
                   resume_prepare_median_ms=statistics.median(prepare_ns)/1e6,
                   resume_context_utf8_bytes=packet['context_bytes'],
                   resume_instruction_utf8_bytes=len(continuity.prompt().encode()),
                   additional_model_calls=0, additional_embeddings=0,
                   active_checkpoints=len(panel._paused()), checkpoint_metadata_bytes=len(metadata),
                   serialized_message_additional_bytes=after-before, synthetic_disk_bytes=file.stat().st_size,
                   python_traced_current_bytes=current, python_traced_peak_bytes=peak),
        limits='Bytes are not measured provider tokens; memory excludes native Qt allocations and this is not a hardware/model benchmark.')
    with continuity.use(packet):
        report['after']['resume_instruction_utf8_bytes'] = len(continuity.prompt().encode())
    output = Path(__file__).resolve().parents[1]/'reports/U115-interrupt-performance-latest.json'
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert not baseline_released and len(panel._paused()) == 8
