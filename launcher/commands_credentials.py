"""Credentials commands.

handle(runtime, text, cmd, cfg, history) returns a command result,
an intentional None (defer to chat), or UNHANDLED. Called in the
original precedence order by command_dispatch; no widgets are loaded.
"""
from __future__ import annotations

from command_runtime import CommandRuntime, UNHANDLED


def handle(runtime: CommandRuntime, text: str, cmd: str, cfg: dict, history: list[dict]):
    if cmd.startswith("key "):
        new_key = text[4:].strip()
        if new_key.startswith(("sk-", "sk_")):
            cfg["openai_key"] = new_key
            runtime._save_key("openai_key", new_key)
            live = runtime._probe_openai(new_key)
            return runtime.TextResult(
                "That's an OpenAI key — routed to the OpenAI slot.\n"
                f"OpenAI: {'connected' if live else 'unreachable'}"
            )
        cfg["api_key"] = new_key
        runtime._save_key("api_key", new_key)
        live = runtime._probe_xai(new_key)
        return runtime.TextResult(f"xAI: {'connected' if live else 'unreachable'}")

    if cmd.startswith("openai "):
        new_key = text[7:].strip()
        if new_key.startswith("xai-"):
            cfg["api_key"] = new_key
            runtime._save_key("api_key", new_key)
            return runtime.TextResult(f"That's an xAI key — routed to the xAI slot. {'connected' if runtime._probe_xai(new_key) else 'unreachable'}")
        if new_key.startswith("sk-ant-"):
            cfg["anthropic_key"] = new_key
            runtime._save_key("anthropic_key", new_key)
            return runtime.TextResult(f"That's an Anthropic key — routed to the Anthropic slot. {'connected' if runtime._probe_claude(new_key) else 'unreachable'}")
        cfg["openai_key"] = new_key
        runtime._save_key("openai_key", new_key)
        return runtime.TextResult(f"OpenAI: {'connected' if runtime._probe_openai(new_key) else 'unreachable'}")

    # Free Cloudflare Workers AI account -- used for free image generation.
    if cmd.startswith("cloudflare "):
        parts = text.split()
        if len(parts) != 3:
            return runtime.TextResult("Usage: cloudflare <account-id> <api-token>\n\n" + runtime.IMAGE_GEN_CLOUDFLARE_HOWTO)
        cfg["cf_account_id"], cfg["cf_api_token"] = parts[1], parts[2]
        runtime._save_key("cf_account_id", parts[1])
        runtime._save_key("cf_api_token", parts[2])
        return runtime.TextResult("Cloudflare saved — free image generation is on. Try: image a lighthouse at dawn")

    if cmd.startswith("anthropic "):
        new_key = text[10:].strip()
        if new_key.startswith("xai-"):
            cfg["api_key"] = new_key
            runtime._save_key("api_key", new_key)
            return runtime.TextResult(f"That's an xAI key — routed to the xAI slot. {'connected' if runtime._probe_xai(new_key) else 'unreachable'}")
        if new_key.startswith("sk-") and not new_key.startswith("sk-ant-"):
            cfg["openai_key"] = new_key
            runtime._save_key("openai_key", new_key)
            return runtime.TextResult(f"That's an OpenAI key — routed to the OpenAI slot. {'connected' if runtime._probe_openai(new_key) else 'unreachable'}")
        cfg["anthropic_key"] = new_key
        runtime._save_key("anthropic_key", new_key)
        return runtime.TextResult(f"Claude: {'connected' if runtime._probe_claude(new_key) else 'unreachable'}")

    # ── Codex / Hermes / Reference Brain ────────────────────────────────
    return UNHANDLED
