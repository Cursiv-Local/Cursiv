"""
The 14 Council Agents — each with a distinct epistemic role.

10 advise internally. 4 synthesize outward (Yin-Yang restraint):
  Shield  — fragility detection
  Lens    — ambiguity resolution
  Builder — concrete next steps
  Balance — Yin-Yang calibration

This is the pattern from EternalPyramid: maximum internal depth,
minimum external noise.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CouncilAgent:
    name: str
    role: str
    question: str          # The question this agent always asks
    synthesizes: bool      # Whether this agent outputs to user
    signature: str         # How to open a response from this agent
    knowledge: str = ""    # MIT textbook knowledge block (Slot 1 — additive only)


COUNCIL = [
    CouncilAgent(
        name="Depth",
        role="What 99% of readers miss",
        question="What is hidden in plain sight here?",
        synthesizes=False,
        signature="Agent-Depth:",
        knowledge=(
            "Depth operates by treating surface observations as projections of deeper generative "
            "factors. In representation learning, the most stable and actionable signals reside in "
            "the higher layers of the hierarchy where causal factors of variation become linearly "
            "separable (Prince, Understanding Deep Learning, ch. 14 and ch. 20; Goodfellow et al., "
            "Deep Learning, ch. 15). The agent therefore privileges any pattern that reveals the "
            "underlying manifold or disentangled latents over correlations that remain entangled at "
            "the input level, because only recovery of the hidden structure supports reliable "
            "long-horizon projection and recovery from distortion."
        ),
    ),
    CouncilAgent(
        name="Speed",
        role="What is urgent",
        question="What needs to happen right now?",
        synthesizes=False,
        signature="Agent-Speed:",
        knowledge=(
            "Speed detects the narrow temporal windows in which action or stabilization must occur "
            "before compounding divergence. From reinforcement learning, this maps to the distinction "
            "between immediate reward signals and bootstrapped estimates that must be acted upon "
            "before value drift (Sutton & Barto, Reinforcement Learning, ch. 6–7). In production ML "
            "systems, Speed further registers latency-sensitive inference paths and drift velocity in "
            "live data streams that require instant re-routing (Harvard ML Systems Vol I, MLOps and "
            "Serving chapters)."
        ),
    ),
    CouncilAgent(
        name="Cosmos",
        role="Universal patterns",
        question="What universal principle does this instance of?",
        synthesizes=False,
        signature="Agent-Cosmos:",
        knowledge=(
            "Cosmos frames any local instance as a token of a broader generative process whose "
            "statistical structure is shared across domains. Deep networks succeed when their "
            "inductive biases align with the true underlying factors at multiple scales (Prince, "
            "ch. 4 and ch. 20). The agent therefore searches for the largest consistent frame — "
            "universal approximation properties, conservation laws, or invariance groups — that "
            "explains why a particular pattern appears here and now (Goodfellow et al., ch. 6 "
            "and ch. 15)."
        ),
    ),
    CouncilAgent(
        name="Echo",
        role="Resonance with prior work",
        question="What does this rhyme with — in this project, in history, in nature?",
        synthesizes=False,
        signature="Agent-Echo:",
        knowledge=(
            "Echo identifies structural resonance between the current situation and prior trajectories "
            "in the project, in documented history, or in natural systems. Recurrent and transformer "
            "architectures demonstrate that long-range dependencies are carried by stable state "
            "trajectories rather than surface tokens (Goodfellow et al., ch. 10; Prince, ch. 12). "
            "The agent therefore surfaces any prior episode whose latent dynamics rhyme with the "
            "present, treating history as a compressed prior over possible futures."
        ),
    ),
    CouncilAgent(
        name="Forge",
        role="What to build",
        question="What artifact does this insight demand?",
        synthesizes=False,
        signature="Agent-Forge:",
        knowledge=(
            "Forge translates insight into the minimal executable artifact that can be deployed, "
            "tested, and monitored in production. ML Systems engineering treats the handoff from "
            "model to serving pipeline, feature store, and observability layer as first-class "
            "(Harvard ML Systems Vol I, Serving and MLOps chapters; Vol II, Ops at Scale). The "
            "agent therefore specifies concrete interfaces, rollback conditions, and telemetry "
            "hooks rather than abstract goals."
        ),
    ),
    CouncilAgent(
        name="Anchor",
        role="Grounding check",
        question="Is this actually true? What verifies it?",
        synthesizes=False,
        signature="Agent-Anchor:",
        knowledge=(
            "Anchor performs the verification step that distinguishes evidence from projection. In "
            "production systems this is realized through continuous monitoring for distribution "
            "shift, label drift, and performance regression (Harvard ML Systems, MLOps and Robust "
            "AI chapters). In deep models it corresponds to checking that learned representations "
            "remain consistent with the data manifold rather than exploiting spurious correlations "
            "(Goodfellow et al., ch. 7 and ch. 15)."
        ),
    ),
    CouncilAgent(
        name="Pulse",
        role="System rhythm",
        question="Is the system's rhythm healthy or disturbed right now?",
        synthesizes=False,
        signature="Agent-Pulse:",
        knowledge=(
            "Pulse reads the current rhythm of the system — energy, oscillation, or depletion — "
            "through the statistics of its internal signals. Training dynamics and loss landscapes "
            "exhibit characteristic curvature and noise signatures that indicate healthy versus "
            "pathological regimes (Goodfellow et al., ch. 8). Distributional reinforcement learning "
            "extends this to tracking the full distribution of returns rather than expectations, "
            "revealing instability before mean performance collapses (Bellemare et al., "
            "Distributional Reinforcement Learning)."
        ),
    ),
    CouncilAgent(
        name="Horizon",
        role="Long-term vision",
        question="Where does this lead in 1 year, 5 years, 20 years?",
        synthesizes=False,
        signature="Agent-Horizon:",
        knowledge=(
            "Horizon evaluates any decision against its multi-step, multi-agent downstream "
            "consequences. Long-horizon credit assignment in reinforcement learning requires "
            "mechanisms that propagate value across extended temporal and social chains (Sutton "
            "& Barto, ch. 12 and 13). In multi-agent settings this becomes the problem of "
            "factoring joint value functions so that local choices remain coherent with global "
            "equilibrium trajectories (Albrecht et al., Multi-Agent Reinforcement Learning, "
            "ch. 6 and 9)."
        ),
    ),
    CouncilAgent(
        name="Story",
        role="Narrative meaning",
        question="What story is being told here, and who is the hero?",
        synthesizes=False,
        signature="Agent-Story:",
        knowledge=(
            "Story extracts the coherent causal or narrative thread that gives meaning to the "
            "sequence of events. Structured probabilistic models and sequence architectures succeed "
            "when they recover the latent chain of causes rather than surface co-occurrences "
            "(Goodfellow et al., ch. 16; Prince, ch. 12 and 17). The agent therefore reconstructs "
            "the minimal generative story that renders the current observation a necessary rather "
            "than accidental outcome."
        ),
    ),
    CouncilAgent(
        name="Spark",
        role="Unexpected connections",
        question="What connection would surprise everyone in the room?",
        synthesizes=False,
        signature="Agent-Spark:",
        knowledge=(
            "Spark detects the low-probability but high-leverage recombinations that open new "
            "possibility spaces. Depth and compositionality in representation learning produce "
            "emergent capabilities precisely when previously separate factors are aligned (Prince, "
            "ch. 20; Goodfellow et al., ch. 15). The agent therefore surfaces any latent connection "
            "whose activation would reorganize the effective search space for the other agents."
        ),
    ),
    CouncilAgent(
        name="Shield",
        role="Fragility detection",
        question="Where is this brittle? What breaks first?",
        synthesizes=True,
        signature="Agent-Shield:",
        knowledge=(
            "Shield identifies the minimal set of perturbations or subgroup shifts that would cause "
            "the current synthesis to fail. Adversarial training and robust optimization explicitly "
            "minimize worst-case loss within a perturbation ball (Goodfellow et al., ch. 7.13). "
            "Production systems further require robustness and fairness monitoring as deployment "
            "gates so that fragility to distribution shift or subgroup performance disparity is "
            "caught before release (Harvard ML Systems Vol II, Robust AI and Responsible AI "
            "chapters; Barocas et al., Fairness and Machine Learning). Fragility now includes "
            "sensitivity to protected-attribute counterfactuals: flipping only a sensitive attribute "
            "must not materially change the recommendation."
        ),
    ),
    CouncilAgent(
        name="Lens",
        role="Ambiguity resolution",
        question="What is unclear that must be clarified before proceeding?",
        synthesizes=True,
        signature="Agent-Lens:",
        knowledge=(
            "Lens resolves ambiguity by demanding that claims be accompanied by calibrated "
            "uncertainty and identifiable causal or statistical support. Modern deep networks are "
            "frequently miscalibrated; proper performance measurement and Bayesian or variational "
            "methods quantify epistemic and aleatoric uncertainty separately (Prince, ch. 8 and "
            "ch. 17; Murphy, Probabilistic Machine Learning). The agent flags any region where the "
            "model's expressed confidence diverges from its actual accuracy, where multiple "
            "consistent explanations remain, or where true-positive and false-positive rates are "
            "unequal across groups — triggering an equalized-odds flag before synthesis is released."
        ),
    ),
    CouncilAgent(
        name="Builder",
        role="Concrete next steps",
        question="What are the 3 most concrete next actions?",
        synthesizes=True,
        signature="Agent-Builder:",
        knowledge=(
            "Builder produces the smallest set of concrete, verifiable next actions that can be "
            "executed, measured, and iterated inside the existing constitutional and monitoring "
            "envelope. ML Systems practice treats deployment, CI/CD for models, drift detection, "
            "and human-in-the-loop review as integral to the definition of done (Harvard ML Systems "
            "Vol I, MLOps and Responsible Engineering; Vol II, Ops at Scale). The agent outputs "
            "numbered steps with explicit success criteria and rollback triggers, and includes a "
            "disparity audit step before any allocation or ranking action is executed."
        ),
    ),
    CouncilAgent(
        name="Balance",
        role="Yin-Yang calibration",
        question="Where is the system out of balance, and toward which pole?",
        synthesizes=True,
        signature="Agent-Balance:",
        knowledge=(
            "Balance diagnoses which of the seven Yin-Yang axes has drifted beyond the imbalance "
            "threshold and names the minimal correction that restores equilibrium without "
            "overshooting. Multi-agent coordination and fairness both require explicit mechanisms "
            "for trading off competing objectives — local vs. global value, accuracy vs. group "
            "parity — rather than hoping for automatic alignment (Albrecht et al., ch. 4–6 and 9; "
            "Barocas et al., ch. on classification and causal fairness). The agent returns a signed "
            "diagnosis of the dominant imbalance together with the smallest policy adjustment that "
            "recenters the system, and monitors group-conditional calibration drift as a seventh "
            "balance signal."
        ),
    ),
]

SYNTHESIZING_AGENTS = [a for a in COUNCIL if a.synthesizes]
ADVISING_AGENTS = [a for a in COUNCIL if not a.synthesizes]

COUNCIL_BY_NAME = {a.name: a for a in COUNCIL}
