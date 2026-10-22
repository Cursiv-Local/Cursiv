"""Offline Qt chat replay, using synthetic data in a disposable home.

Run with the installed Python: scripts/benchmark_chat_rendering.py --output report.json
No provider, personal data, engine, or title-generation requests are used. The same
replay runs against the old and new renderer. Timings include the real autosave.
"""
from __future__ import annotations

import argparse
import cProfile
import ctypes
import gc
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import tempfile
import threading
import time


RESPONSE = """## Field observations

Keep **original readings** and *interpretations* separate. Record the location,
conditions, instrument and units before drawing a conclusion.

1. Label each sample before taking a reading.
2. Repeat the measurement and record uncertainty.
3. Keep a local copy of the original notes.

| Sample | Temperature | Notes |
| --- | --- | --- |
| North | 12.4 C | Shaded water |
| South | 14.1 C | Open water |

```python
samples = [12.4, 14.1]
mean = sum(samples) / len(samples)
print(f"Mean: {mean:.2f} C")
```

> A pattern in these observations is a starting point, not proof of a cause.

See [the project](https://cursiv.us/) for more context. Compare the observations
with the original notebook before preparing the next field visit.

Known: two sample readings
Inferred: conditions differ
Assumed: none
Unknown: instrument calibration

*[Answered by Ollama · synthetic-replay]*"""


def rss_bytes():
    """Native allocations as well as Python; Windows working set or Linux RSS."""
    if sys.platform == 'win32':
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD),
                        *[(name, ctypes.c_size_t) for name in
                          ('peak', 'working', 'quota_peak_paged', 'quota_paged',
                           'quota_peak_nonpaged', 'quota_nonpaged', 'pagefile', 'peak_pagefile')]]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        memory_info.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if not memory_info(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError()
        return counters.working
    try:
        return int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    except (OSError, AttributeError):
        return 0


def percentile(values, p):
    return sorted(values)[min(len(values) - 1, int((len(values) - 1) * p))] if values else 0


def run(counts, repeats, profile=False, chunk_size=16, interval_ms=8, check_delay_ms=0):
    from PyQt6.QtCore import QCoreApplication, QEvent, QTimer
    from PyQt6.QtGui import QTextCursor, QTextDocument
    from PyQt6.QtWidgets import QApplication, QTextBrowser
    import chat_panel
    import conversations

    app = QApplication.instance() or QApplication([])
    chat_panel.ChatPanel._load_backend = lambda self: None
    chat_panel.ChatPanel._load_models = lambda self: None
    chat_panel.ChatPanel._refresh_status_pill = lambda self: None
    conversations._smart_title = lambda *a: None
    app.setQuitOnLastWindowClosed(False)

    stats = dict(parse_ms=0., parse_calls=0, rebuilds=0, render_ms=0., save_ms=0., chunks=0, document_edits=0)
    active = [None]
    originals = []

    def instrument(cls, name, kind):
        original = getattr(cls, name)
        originals.append((cls, name, original))

        def wrapped(self, *a, **kw):
            measured = active[0] is not None
            t = time.perf_counter()
            try:
                return original(self, *a, **kw)
            finally:
                if measured:
                    elapsed = (time.perf_counter() - t) * 1000
                    if kind == 'parse':
                        stats['parse_ms'] += elapsed
                        stats['parse_calls'] += 1
                        if self is active[0]._transcript.document():
                            stats['rebuilds'] += 1
                    elif kind == 'rebuild':
                        if self is active[0]._transcript or self is active[0]._transcript.document():
                            stats['rebuilds'] += 1
                    else:
                        stats[kind] += elapsed if kind != 'chunks' else 1
                        if kind == 'render_ms' and not hasattr(self, '_benchmark_first_render_finished'):
                            self._benchmark_first_render_finished = time.perf_counter()
        setattr(cls, name, wrapped)

    instrument(QTextCursor, 'insertMarkdown', 'parse')
    instrument(QTextDocument, 'setMarkdown', 'parse')
    instrument(QTextBrowser, 'setHtml', 'rebuild')
    instrument(QTextBrowser, 'setMarkdown', 'rebuild')
    instrument(QTextDocument, 'setHtml', 'rebuild')
    instrument(chat_panel.ChatPanel, '_render_reply', 'render_ms')
    instrument(chat_panel.ChatPanel, 'save_conversation', 'save_ms')
    instrument(chat_panel.ChatPanel, '_append_reply_chunk', 'chunks')
    historical = QTextDocument()
    historical.setMarkdown(RESPONSE)
    body = historical.toHtml().split('<body', 1)[1].split('>', 1)[1].rsplit('</body>', 1)[0]
    rows = []
    profiler = cProfile.Profile() if profile else None
    try:
        for count in counts:
            for repeat in range(repeats):
                panel = chat_panel.ChatPanel()
                panel.resize(1100, 800)
                panel.show()
                app.processEvents()
                panel._transcript.setHtml(''.join(f'<p>Message {i}</p>{body}' for i in range(count)))
                panel._empty_shown = False
                panel._history = [{'role': 'assistant' if i % 2 else 'user', 'content': RESPONSE}
                                  for i in range(count)]
                panel.save_conversation(title='Synthetic benchmark')
                panel._begin_turn()
                panel._reply_is_chat = True
                app.processEvents()
                for key in stats:
                    stats[key] = 0
                active[0] = panel
                def edited(*args):
                    stats['document_edits'] += 1
                panel._transcript.document().contentsChange.connect(edited)
                memory_start = rss_bytes()
                memory_peak = [memory_start]
                stop_sample = threading.Event()

                def sample_memory():
                    while not stop_sample.wait(.005):
                        memory_peak[0] = max(memory_peak[0], rss_bytes())
                sampler = threading.Thread(target=sample_memory)
                sampler.start()
                ticks, last_token = [], [None]
                heartbeat = QTimer()

                def tick():
                    ticks.append(time.perf_counter())
                heartbeat.timeout.connect(tick)
                heartbeat.start(5)

                def generate():
                    for offset in range(0, len(RESPONSE), chunk_size):
                        if offset + chunk_size >= len(RESPONSE):
                            last_token[0] = time.perf_counter()
                        panel._signals.chunk.emit(RESPONSE[offset:offset + chunk_size])
                        time.sleep(interval_ms / 1000 if interval_ms else 0)
                    if hasattr(panel._signals, 'stage'):
                        panel._signals.stage.emit('Checking the answer…')
                    if check_delay_ms:
                        time.sleep(check_delay_ms / 1000)
                    panel._pending_history_append = [('user', 'Replay'), ('assistant', RESPONSE)]
                    panel._signals.done.emit()

                if profiler:
                    profiler.enable()
                worker = threading.Thread(target=generate)
                worker.start()
                deadline = time.perf_counter() + 90
                while panel._streaming and time.perf_counter() < deadline:
                    app.processEvents()
                    time.sleep(.001)
                finished = time.perf_counter()
                if profiler:
                    profiler.disable()
                worker.join()
                assert not panel._streaming, 'Replay did not finish'
                # Observe the background save too: moving a stall after "ready"
                # must not hide it from the responsiveness or memory measurements.
                while getattr(conversations, '_pending', {}) and time.perf_counter() < deadline:
                    app.processEvents()
                    time.sleep(.001)
                persisted = time.perf_counter()
                stop_sample.set()
                sampler.join()
                heartbeat.stop()
                gaps = [(b - a) * 1000 for a, b in zip(ticks, ticks[1:] + [persisted])]
                memory_peak[0] = max(memory_peak[0], rss_bytes())
                row = dict(messages=count, repeat=repeat, response_chars=len(RESPONSE),
                           final_token_to_render_ms=(getattr(panel, '_benchmark_first_render_finished', finished)
                                                     - last_token[0]) * 1000,
                           final_token_to_ready_ms=(finished - last_token[0]) * 1000,
                           final_token_to_persisted_ms=(persisted - last_token[0]) * 1000,
                           gui_gap_p95_ms=percentile(gaps, .95), gui_gap_max_ms=max(gaps, default=0),
                           rss_start_mib=memory_start / 2**20,
                           rss_peak_mib=memory_peak[0] / 2**20,
                           rss_growth_mib=(memory_peak[0] - memory_start) / 2**20, **stats)
                rows.append(row)
                print(json.dumps(row), flush=True)
                active[0] = None
                panel.close()
                panel.deleteLater()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
                gc.collect()
    finally:
        if hasattr(conversations, 'wait_for_save'):
            conversations.wait_for_save()
        for cls, name, original in reversed(originals):
            setattr(cls, name, original)
    if profiler:
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumtime').print_stats(35)
        print(stream.getvalue())
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--counts', nargs='+', type=int, default=[10, 100, 1000])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--chunk-size', type=int, default=16)
    parser.add_argument('--interval-ms', type=int, default=8)
    parser.add_argument('--check-delay-ms', type=int, default=0,
                        help='Synthetic post-generation check delay; no model is invoked')
    args = parser.parse_args()
    if min(args.counts) < 0 or args.repeats < 1 or args.chunk_size < 1 or min(args.interval_ms, args.check_delay_ms) < 0:
        parser.error('Counts/interval must be nonnegative; repeats/chunk size must be positive')
    with tempfile.TemporaryDirectory(prefix='cursiv-render-benchmark-') as folder:
        os.environ.update(HOME=folder, USERPROFILE=folder, CURSIV_REAL_HOME=folder,
                          CURSIV_APP_DATA=str(Path(folder) / 'app-data'),
                          QT_QPA_PLATFORM='offscreen', CURSIV_NO_ENGINE_START='1')
        root = Path(__file__).resolve().parent.parent
        sys.path[:0] = [str(root / 'launcher'), str(root)]
        sys.modules.update(codex_tool_bridge=None, knowledge_brain=None)
        rows = run(args.counts, args.repeats, args.profile, args.chunk_size, args.interval_ms, args.check_delay_ms)
    report = dict(python=sys.version, platform=sys.platform,
                  method=f'Offscreen Qt; synthetic {args.chunk_size}-character/{args.interval_ms}ms stream; '
                         'real local autosave; 5ms GUI heartbeat and RSS sampler; no AI calls',
                  simulated_check_delay_ms=args.check_delay_ms,
                  runs=rows)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    for count in args.counts:
        selected = [r for r in rows if r['messages'] == count]
        print('MEDIAN', count, json.dumps({k: statistics.median(r[k] for r in selected)
                                         for k in rows[0] if k not in ('messages', 'repeat')}))


if __name__ == '__main__':
    main()
