"""
Council Letter Reader — authorized council walkthrough of sealed letters.

A sealed letter can be walked through by the council only when requested
by the sender OR the recipient. The letter is decrypted in memory,
passed to the 14 council agents for deliberation, and the result returned.

The council reports on:
  — What the letter carries (Depth, Story, Echo)
  — What the emotional weight is (Pulse, Balance)
  — Where it might land differently than intended (Shield, Lens)
  — What the recipient needs to understand (Builder, Horizon)
  — What's being said beneath what's written (Spark, Anchor)

The raw letter text is NEVER included in the council's output.
The council reports a reading, not a transcript.
All deliberation runs locally via Ollama — the letter never leaves the machine.
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any

from cursiv_engine.postal.sealed_store import get_sealed_entry, open_letter

_OLLAMA_URL   = "http://127.0.0.1:11434/api/chat"
_OLLAMA_MODEL = "llama3.1"

# ── Letter-specific council questions ────────────────────────────────────────
_LETTER_AGENT_FRAMES: dict[str, str] = {
    "Depth":   "What is the sender not saying directly? What is written between the lines?",
    "Speed":   "What in this letter is urgent — what must the recipient hear right now?",
    "Cosmos":  "What universal pattern is this letter an instance of? What archetype is being enacted?",
    "Echo":    "What prior wound, joy, or unresolved moment does this letter touch?",
    "Forge":   "What does this letter demand? What action or response does it require?",
    "Anchor":  "What is actually true in this letter? What claim needs grounding?",
    "Pulse":   "What is the emotional rhythm of this letter? Is it healthy, distressed, or masked?",
    "Horizon": "Where does this letter lead? What relationship trajectory does it set in motion?",
    "Story":   "What story is being told? Who is the hero, and what is the wound?",
    "Spark":   "What unexpected connection does this letter contain that even the sender may not see?",
    "Shield":  "Where is this letter fragile? What might land differently than intended?",
    "Lens":    "What ambiguity in this letter needs to be resolved before it can be received correctly?",
    "Builder": "What three concrete things does the recipient need from this letter?",
    "Balance": "Where is the balance off? What would bring the relationship back to equilibrium?",
}


def _make_ollama_caller(ollama_url: str, model: str):
    """Create a synchronous LLM caller via Ollama — fully local, no external APIs."""
    def call(prompt: str) -> str:
        payload = json.dumps({
            "model":    model,
            "messages": [{"role": "user", "content": prompt}],
            "stream":   False,
        }).encode("utf-8")
        req = urllib.request.Request(
            ollama_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
                return data.get("message", {}).get("content", "")
        except Exception as exc:
            return f"[{type(exc).__name__}]"
    return call


def _format_council_reading(result: dict[str, Any], entry: dict, relation: str) -> str:
    """Format the council's deliberation result as a letter reading."""
    lines = [
        f"  ⬡ COUNCIL READING",
        f"  ─────────────────────────────────────────────────────────",
        f"  from:       {entry.get('from_display', entry['from_key'])}",
        f"  to:         {entry.get('for_display', entry['for_key'])}",
        f"  written:    {entry.get('sealed', '')[:10]}",
        f"  authorized: {relation}",
        f"  ─────────────────────────────────────────────────────────",
        "",
    ]

    internal = result.get("internal_perspectives", {})
    syntheses = result.get("external_syntheses", {})
    combined = result.get("combined", "")

    # Show selected internal perspectives (the most letter-relevant agents)
    reading_agents = ["Depth", "Echo", "Pulse", "Story", "Shield", "Spark"]
    for agent_name in reading_agents:
        perspective = internal.get(agent_name, "")
        if perspective and not perspective.startswith("["):
            lines.append(f"  [{agent_name}]")
            lines.append(f"  {perspective}")
            lines.append("")

    lines.append(f"  ─────────────────────────────────────────────────────────")
    lines.append(f"  SYNTHESIS")
    lines.append("")
    if combined:
        # Wrap combined text
        for para in combined.split("\n\n"):
            if para.strip():
                lines.append(f"  {para.strip()}")
                lines.append("")

    lines.append(f"  ─────────────────────────────────────────────────────────")
    return "\n".join(lines)


def council_walkthrough(
    letter_id:        str,
    requesting_user:  str,
    cfg:              dict,
    *,
    show_progress_cb: "callable | None" = None,
) -> str:
    """
    Decrypt a sealed letter and run a full council reading.

    requesting_user must be the sender or recipient key.
    All deliberation runs locally via Ollama — letter content never leaves
    this machine.

    Returns a formatted council reading string, or an error message.
    """
    entry = get_sealed_entry(letter_id)
    if not entry:
        return "  [Letter not found in this vault.]"

    if requesting_user not in (entry["from_key"], entry["for_key"]):
        return (
            "  [Access denied — only the sender or recipient may request"
            " a council reading of this letter.]"
        )

    if show_progress_cb:
        show_progress_cb("decrypting")

    content = open_letter(letter_id)
    if content is None:
        return (
            "  [Decryption failed — this letter cannot be opened on this machine.\n"
            "  It was sealed on a different Cursiv installation.]"
        )

    if show_progress_cb:
        show_progress_cb("deliberating")

    relation = (
        "sender (reading what you wrote)"
        if requesting_user == entry["from_key"]
        else "recipient (reading what was sent to you)"
    )

    ollama_url   = cfg.get("ollama_url",   _OLLAMA_URL)
    ollama_model = cfg.get("ollama_model", _OLLAMA_MODEL)

    # Build the council query — does not include raw letter text in the synthesis output
    query = (
        f"[COUNCIL LETTER READING — authorized by {requesting_user}, {relation}]\n\n"
        f"From: {entry.get('from_display', entry['from_key'])}\n"
        f"To: {entry.get('for_display', entry['for_key'])}\n"
        f"Written: {entry.get('sealed', '')[:10]}\n\n"
        f"Letter:\n{content}\n\n"
        f"Provide a deep reading of this letter through your specific lens: {_LETTER_AGENT_FRAMES.get('Depth', '')}\n"
        f"Be specific about what this particular letter carries. Do not summarize — deliberate.\n"
        f"The requesting principal is the {relation.split('(')[0].strip()}."
    )

    agent_context = {
        "name":             "Council Letter Reader",
        "domain":           "sealed personal correspondence",
        "identity_anchor":  f"reading a private letter for {requesting_user}",
        "capabilities":     ["deep reading", "emotional intelligence", "letter analysis"],
        "council_position": f"{requesting_user} has authorized this council reading",
    }

    try:
        from cursiv_engine.council.deliberation import CouncilDeliberation
        llm_caller = _make_ollama_caller(ollama_url, ollama_model)
        cd     = CouncilDeliberation(llm_caller)
        result = cd.deliberate(query, agent_context)
        return _format_council_reading(result, entry, relation)

    except Exception as exc:
        return (
            f"  [Council unavailable: {type(exc).__name__}]\n"
            f"  Is Ollama running? (ollama serve)\n"
            f"  Letter was decrypted successfully — council processing failed."
        )
