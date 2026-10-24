"""Chat provider tools.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _call_claude_with_tools, _call_xai_with_tools, _call_openai_with_tools.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _call_claude_with_tools(runtime: ChatRuntime, messages: list[dict], anthropic_key: str, root: Path, confirm_writes: bool, max_tokens: int, max_loops: int, on_action) -> Generator[str, None, None]:
    """
    Agentic file-access loop using Claude's native tool-calling API.
    Uses a compact system prompt (~200 tokens) instead of the full 12k-token
    codex to stay under the 30k input-tokens/min rate limit.
    """
    system_str = runtime._compact_system_for_tools() + runtime.turn_policy.current().note()
    # The first block is the replaceable persona. Retain application-owned
    # current-state/source blocks when this provider switches to its tool prompt.
    system_str += '\n'.join(m['content'] for m in messages[1:] if m.get('role') == 'system')
    # Keep only the last 8 user/assistant turns to limit history overhead
    chat_only  = [m for m in messages if m["role"] in ("user", "assistant")]
    loop_msgs  = chat_only[-16:]   # 8 pairs = 16 messages
    file_results = []

    import time as _time

    for _ in range(max_loops):
        payload = runtime.json.dumps({
            "model":      runtime.ANTHROPIC_CODE_MODEL,
            "max_tokens": max_tokens,
            "system":     system_str,
            "tools":      runtime.CLAUDE_TOOLS,
            "messages":   loop_msgs,
        }).encode()

        # Pre-call rate gate: wait if we're near the 20k TPM ceiling
        if runtime._rate_limiter:
            est = runtime._rate_limiter.estimate_tokens(payload.decode(errors="ignore"))
            runtime._rate_limiter.wait_if_needed(est)

        for attempt in range(3):
            try:
                req = runtime.urllib.request.Request(
                    runtime.ANTHROPIC_URL, data=payload,
                    headers={
                        "content-type":      "application/json",
                        "x-api-key":         anthropic_key,
                        "anthropic-version": runtime.ANTHROPIC_VERSION,
                    },
                )
                with runtime.urllib.request.urlopen(req, timeout=120) as resp:
                    data = runtime.json.loads(resp.read().decode())
                # Record actual tokens used so the window stays accurate
                if runtime._rate_limiter:
                    usage   = data.get("usage", {})
                    actual  = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    if actual:
                        runtime._rate_limiter.record_actual(actual)
                break   # success
            except runtime.urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")
                if e.code == 429 and attempt < 2:
                    wait_s = 15 * (attempt + 1)   # 15s, then 30s
                    yield f"\n*[Rate gate: pacing {wait_s}s — TPM window full]*\n"
                    _time.sleep(wait_s)
                    continue
                yield f"\n[Claude error {e.code}: {body[:200]}]"
                return
            except Exception as e:
                yield f"\n[Claude error: {e}]"
                return

        stop_reason    = data.get("stop_reason", "end_turn")
        content_blocks = data.get("content", [])

        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(block)

        if (stop_reason == 'end_turn' or not tool_calls) and any(
                r.operation not in ('read_file', 'list_directory', 'search_files') for r in file_results):
            return                  # action acknowledgements already came from the backend
        if text_parts and not tool_calls:
            from cursiv_engine.core.file_access import model_prose
            visible = model_prose(' '.join(text_parts))
            for word in visible.split(" "):
                yield word + " "

        if stop_reason == "end_turn" or not tool_calls:
            return

        loop_msgs.append({"role": "assistant", "content": content_blocks})

        tool_results = []
        for tc in tool_calls:
            fn_name = tc["name"]
            fn_args = tc.get("input", {})
            tc_id   = tc["id"]

            if fn_name == "write_file" and not runtime.turn_policy.current().blocks(fn_name) and (confirm_writes or runtime._existing_file(fn_args, root)):
                try:
                    request = runtime._pending_file(fn_args, root)
                except (OSError, ValueError, TypeError) as exc:
                    from cursiv_engine.core.file_access import FileResult, VerifiedText
                    failed = FileResult(fn_name, ok=False, error=f'{type(exc).__name__}: {exc}')
                    file_results.append(failed)
                    if on_action:
                        on_action(failed)
                    yield VerifiedText(failed.render() + '\n', failed)
                    tool_results.append({'type': 'tool_result', 'tool_use_id': tc_id,
                                         'content': failed.model_output(), 'is_error': True})
                    runtime._CURSIV_REPLY = True
                    return
                path_arg    = request['path']
                content_arg = fn_args.get("content", "")
                preview     = content_arg[:400] + ("…" if len(content_arg) > 400 else "")
                yield (
                    f"\n**Write requested:** `{path_arg}`\n"
                    f"```\n{preview}\n```\n"
                    f"*Waiting for approval…*\n"
                )
                yield runtime.WRITE_SENTINEL + runtime.json.dumps(request)
                return

            is_file = fn_name in {'read_file', 'write_file', 'append_file', 'create_file', 'list_directory', 'search_files', 'create_directory', 'delete_file'}
            receipt = runtime._file_tool_result(fn_name, fn_args, root) if is_file else None
            result = receipt.model_output() if receipt else runtime.execute_tool(fn_name, fn_args, root)
            if receipt:
                from cursiv_engine.core.file_access import VerifiedText
                file_results.append(receipt)
                if on_action:
                    on_action(receipt)
                yield VerifiedText(receipt.status_line() + '\n', receipt)
                if not receipt.ok:
                    runtime._CURSIV_REPLY = True
                    return
                ctx_result = result
            elif fn_name == "submit_plan":
                yield f"*`→ plan submitted`*\n"
                ctx_result = result
            else:
                yield f"Unverified tool output ({fn_name}): {result[:120]}\n"
                ctx_result = runtime.json.dumps({'confirmed': False, 'tool': fn_name, 'output': result})

            tool_results.append({
                "type":        "tool_result",
                "tool_use_id": tc_id,
                "content":     ctx_result,
                "is_error":    not receipt.ok if receipt else result.startswith('Error:'),
            })

        loop_msgs.append({"role": "user", "content": tool_results})

    yield "\n[Max tool iterations reached — stopping.]"

def _call_xai_with_tools(runtime: ChatRuntime, messages: list[dict], api_key: str, root: Path, openai_key: str, has_images: bool, max_tokens: int, max_loops: int, confirm_writes: bool, anthropic_key: str, endpoint_url: str, model_override: str, provider_name: str, on_action) -> Generator[str, None, None]:
    """
    Agentic file-access tool loop (OpenAI-compatible API format).
    Works for xAI/Grok and GPT-4.1 — same wire format, different endpoint/model.
    Tool arguments are written exactly; there is no secondary content rewrite.
    """
    url       = endpoint_url or runtime.XAI_URL
    model     = model_override or (runtime.XAI_MODEL_VIS if has_images else runtime.XAI_MODEL)
    loop_msgs = list(messages)
    file_results = []

    for _ in range(max_loops):
        payload = runtime.json.dumps({
            "model":       model,
            "messages":    loop_msgs,
            "tools":       runtime.FILE_TOOLS,
            "tool_choice": "auto",
            "max_tokens":  max_tokens,
            "temperature": 0.7,
            "stream":      False,
        }).encode()
        try:
            req = runtime.urllib.request.Request(
                url, data=payload,
                headers={"Content-Type":  "application/json",
                         "Authorization": f"Bearer {api_key}"},
            )
            with runtime.urllib.request.urlopen(req, timeout=90) as resp:
                data = runtime.json.loads(resp.read().decode())
        except runtime.urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")
            yield f"\n[{provider_name} error {e.code}: {body[:200]}]"
            return
        except Exception as e:
            yield f"\n[{provider_name} error: {e}]"
            return

        choice     = data["choices"][0]
        msg        = choice["message"]
        loop_msgs.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            if any(r.operation not in ('read_file', 'list_directory', 'search_files') for r in file_results):
                return              # never let a model replace the verified action receipts
            # Terminal response — fake-stream word by word for rolling feel
            content = msg.get("content") or ""
            from cursiv_engine.core.file_access import model_prose
            content = model_prose(content)
            for word in content.split(" "):
                yield word + " "
            return

        # Execute each tool call
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = runtime.json.loads(tc["function"]["arguments"])
            except Exception:
                fn_args = {}

            # Confirm-before-write: pause and hand control back to the UI
            if fn_name == "write_file" and not runtime.turn_policy.current().blocks(fn_name) and (confirm_writes or runtime._existing_file(fn_args, root)):
                try:
                    request = runtime._pending_file(fn_args, root)
                except (OSError, ValueError, TypeError) as exc:
                    from cursiv_engine.core.file_access import FileResult, VerifiedText
                    failed = FileResult(fn_name, ok=False, error=f'{type(exc).__name__}: {exc}')
                    file_results.append(failed)
                    if on_action:
                        on_action(failed)
                    yield VerifiedText(failed.render() + '\n', failed)
                    loop_msgs.append({'role': 'tool', 'tool_call_id': tc['id'], 'content': failed.model_output()})
                    runtime._CURSIV_REPLY = True
                    return
                path_arg    = request['path']
                content_arg = fn_args.get("content", "")
                preview     = content_arg[:600] + ("..." if len(content_arg) > 600 else "")
                yield (
                    f"\n**Write requested:** `{path_arg}`\n"
                    f"```\n{preview}\n```\n"
                    f"*Waiting for approval…*\n"
                )
                yield runtime.WRITE_SENTINEL + runtime.json.dumps(request)
                return   # stop the loop — resume after user approves

            is_file = fn_name in {'read_file', 'write_file', 'append_file', 'create_file', 'list_directory', 'search_files', 'create_directory', 'delete_file'}
            receipt = runtime._file_tool_result(fn_name, fn_args, root) if is_file else None
            result = receipt.model_output() if receipt else runtime.execute_tool(fn_name, fn_args, root)
            if receipt:
                from cursiv_engine.core.file_access import VerifiedText
                file_results.append(receipt)
                if on_action:
                    on_action(receipt)
                yield VerifiedText(receipt.status_line() + '\n', receipt)
                if not receipt.ok:
                    runtime._CURSIV_REPLY = True
                    return
                ctx_result = result
            else:
                yield f"Unverified tool output ({fn_name}): {result[:120]}\n"
                ctx_result = runtime.json.dumps({'confirmed': False, 'tool': fn_name, 'output': result})

            loop_msgs.append({
                "role":         "tool",
                "tool_call_id": tc["id"],
                "content":      ctx_result,
            })

    yield "\n[Max tool iterations reached — stopping.]"

def _call_openai_with_tools(runtime: ChatRuntime, messages: list[dict], openai_key: str, root: Path, anthropic_key: str, max_tokens: int, max_loops: int, confirm_writes: bool, on_action) -> Generator[str, None, None]:
    """GPT-4.1 tool loop — same OpenAI-compatible format as xAI, different endpoint/model."""
    yield from runtime._call_xai_with_tools(
        messages, openai_key, root,
        openai_key="",
        has_images=False,
        max_tokens=max_tokens,
        max_loops=max_loops,
        confirm_writes=confirm_writes,
        anthropic_key=anthropic_key,
        endpoint_url=runtime.OPENAI_URL,
        model_override=runtime.OPENAI_CODE_MODEL,
        provider_name="OpenAI",
        on_action=on_action,
    )
