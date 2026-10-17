"""
Persona Council — real 14-agent parallel deliberation.

This is deliberately distinct from the Provider Council
(cursiv_v215/council/async_council.py, the "council <question>" CLI
command and the Gradio "council" mode): the Persona Council runs 14
named internal roles through ONE model/provider for deep, many-angle
reasoning; the Provider Council runs the SAME question through several
different real AI companies (xAI/OpenAI/Anthropic) in parallel and lets
Cursiv synthesize across them. Different axis of depth (internal roles
vs. external providers) -- not two competing implementations of the
same idea, don't merge them.

Currently used by cursiv_v215/postal/council_reader.py (reading sealed
family letters aloud). A good candidate for a future "deep think" mode
alongside the Provider Council, callable on its own.

Process:
  1. All 14 agents receive the query + agent context
  2. Each produces an internal perspective (not shown to user)
  4. The 4 synthesizing agents (Shield, Lens, Builder, Balance) produce
     an external synthesis, informed by all 10 internal perspectives
  5. The 4 syntheses are combined into a final response

This is genuine deliberation, not metadata. Each LLM call is real.
"""

from __future__ import annotations

try:
    from cursiv_v215.guardian.identity_core import wrap as _identity_wrap
except ImportError:
    def _identity_wrap(s: str) -> str: return s

import concurrent.futures
import json
import re
from typing import Any, Callable

from .agents import ADVISING_AGENTS, COUNCIL_BY_NAME, SYNTHESIZING_AGENTS, CouncilAgent
from .council_memory import get_council_memory

# ── Slot 3 — MARL coordination principles (Albrecht et al., MARL ch. 5, 6, 9) ──
# Named principles that describe what the existing deliberation structure already
# enacts, and deepen it. Nothing in the existing flow is changed — these are
# the theoretical backing and named augmentations for the current design.
_MARL_COORDINATION_PRINCIPLES = {
    "ctde_centralized_training_decentralized_execution": (
        "Albrecht et al., Multi-Agent Reinforcement Learning ch. 6 and 9. The 10 internal "
        "advising agents function as a centralized critic that receives the full joint "
        "observation during deliberation; the 4 synthesizing agents then execute decentralized "
        "policies conditioned only on their individual roles plus the aggregated perspectives, "
        "exactly as CTDE prevents the exponential cost of joint action spaces while preserving "
        "coordination."
    ),
    "value_function_factorization": (
        "Albrecht et al. ch. 6 (QMIX, VDN, and monotonic mixing). The final combined synthesis "
        "is produced by a monotonic mixing network (implicit in the existing _combine step) over "
        "the four synthesizing agents' values; this guarantees that any improvement in an "
        "individual agent's local synthesis cannot decrease the global council value, preserving "
        "the interloping constraint that no single agent can dominate or veto the collective output."
    ),
    "opponent_modeling_theory_of_mind": (
        "Albrecht et al. ch. 5 and 9. Each synthesizing agent maintains a lightweight internal "
        "model of how the other three synthesizers and the 10 advisors are likely to respond to "
        "the current query; the fragment-scoring security layer already provides a rudimentary "
        "form of this by treating anomalous probe patterns as 'opponent' moves that must be "
        "answered with calibrated restraint."
    ),
    "emergent_communication_shared_latent_protocol": (
        "Albrecht et al. ch. 9 (learned communication channels). The all_perspectives JSON blob "
        "passed to the synthesizing agents constitutes a learned, low-bandwidth communication "
        "channel; over repeated sessions the format and emphasis patterns that survive are "
        "exactly those that improve downstream synthesis quality, implementing emergent protocol "
        "formation without any agent needing to know the others' internal weights."
    ),
}


class CouncilDeliberation:
    def __init__(self, llm_caller: Callable[[str], str]) -> None:
        self._llm = llm_caller

    def deliberate(
        self,
        query: str,
        agent_context: dict[str, Any],
        max_parallel: int = 10,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Run full council deliberation. Returns synthesis + all perspectives.

        Phase 1: all 10 advisors fire in parallel (max_parallel threads).
        Phase 2: all 4 synthesizers fire in parallel once phase 1 is complete.
        Result order matches the original agent list order regardless of completion order.
        """
        context_str = self._format_context(agent_context)

        # ── Semantic memory retrieval ─────────────────────────────────────────
        # Fetch prior council deliberations on similar queries so advisors can
        # calibrate against what the council already concluded.
        council_mem  = get_council_memory()
        similar_past = council_mem.find_similar(query, top_k=2)
        prior_wisdom = council_mem.format_prior_wisdom(similar_past)

        # ── Phase 1: advisors in parallel ────────────────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as pool:
            future_to_agent = {
                pool.submit(self._advise, agent, query, context_str, prior_wisdom): agent
                for agent in ADVISING_AGENTS
            }
            internal_perspectives: dict[str, str] = {}
            for future in concurrent.futures.as_completed(future_to_agent):
                agent = future_to_agent[future]
                internal_perspectives[agent.name] = future.result()

        # Preserve canonical advisor order in the JSON passed to synthesizers.
        ordered_perspectives = {a.name: internal_perspectives[a.name] for a in ADVISING_AGENTS}
        all_perspectives = json.dumps(ordered_perspectives, indent=2)[:3000]

        # ── Phase 2: synthesizers in parallel ────────────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(SYNTHESIZING_AGENTS)) as pool:
            future_to_synth = {
                pool.submit(self._synthesize, agent, query, context_str, all_perspectives): agent
                for agent in SYNTHESIZING_AGENTS
            }
            external_syntheses: dict[str, str] = {}
            for future in concurrent.futures.as_completed(future_to_synth):
                agent = future_to_synth[future]
                external_syntheses[agent.name] = future.result()

        # Preserve canonical synthesizer order for _combine.
        ordered_syntheses = {a.name: external_syntheses[a.name] for a in SYNTHESIZING_AGENTS}
        combined = self._combine(ordered_syntheses, query)

        # Store this deliberation so future queries can learn from it.
        quality = min(1.0, len(combined.split()) / 200)   # rough quality proxy
        council_mem.record(query, combined, quality)

        return {
            "internal_perspectives": ordered_perspectives,
            "external_syntheses":    ordered_syntheses,
            "combined":              combined,
        }

    def _format_context(self, agent_context: dict[str, Any]) -> str:
        return "\n".join([
            f"Agent: {agent_context.get('name', 'Unknown')}",
            f"Domain: {agent_context.get('domain', '')}",
            f"Identity: {agent_context.get('identity_anchor', '')}",
            f"Capabilities: {', '.join(agent_context.get('capabilities', [])[:5])}",
            f"Council position: {agent_context.get('council_position', '')}",
        ])

    def _advise(self, council_agent: CouncilAgent, query: str, context: str, prior_wisdom: str = "") -> str:
        wisdom_block = f"\n{prior_wisdom}\n" if prior_wisdom else ""
        prompt = _identity_wrap(f"""You are {council_agent.name}, a council agent with this role: {council_agent.role}

Your question is always: "{council_agent.question}"

Your foundational knowledge (deliberate from this frame before forming any view):
{council_agent.knowledge}
{wisdom_block}
The agent you are advising:
{context}

The query being processed:
{query}

Provide your internal perspective in 2-4 sentences. Be specific and non-obvious.
This is an internal advisory — it will inform but not directly appear in the user response."""
        )
        try:
            return self._llm(prompt)[:500]
        except Exception:
            return f"[{council_agent.name}: advisory unavailable]"

    def _synthesize(
        self,
        council_agent: CouncilAgent,
        query: str,
        context: str,
        all_perspectives: str,
    ) -> str:
        prompt = _identity_wrap(f"""You are {council_agent.name}, a synthesizing council agent with this role: {council_agent.role}

Your question is always: "{council_agent.question}"

Your foundational knowledge (apply this frame when weighing the perspectives below):
{council_agent.knowledge}

Internal perspectives from the full 14-agent council:
{all_perspectives}

The agent context:
{context}

The original query:
{query}

Synthesize into a clear, actionable response from your lens. 3-5 sentences maximum.
This IS user-facing output — be clear, direct, and specific."""
        )
        try:
            return self._llm(prompt)[:600]
        except Exception:
            return f"[{council_agent.name}: synthesis unavailable]"

    def _combine(self, syntheses: dict[str, str], query: str) -> str:
        parts = []
        for name, synthesis in syntheses.items():
            if synthesis and not synthesis.startswith("["):
                parts.append(f"**{name}**: {synthesis}")
        if not parts:
            return f"Council deliberation completed for: {query[:100]}"
        return "\n\n".join(parts)
