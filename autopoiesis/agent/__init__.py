"""
Antigravity Organism Subsystem.

An autopoietic, self-evolving living organism architecture:
- Cognitive Metabolism: Ingests session events and digests them into procedural mutations.
- Skill & Rule Autophagy: Audits, refactors, and synthesizes skills and agent rules.
- Cognitive Apoptotic Gate: Immune validation protecting the agent from degradation.
- Generational Lineage Tree: Tracks evolutionary progress across generations (Gen 0 -> Gen N).
"""

from .metabolism import (
    CognitiveMetabolism,
    EventType,
    ProceduralMutationCandidate,
    SessionEvent,
    TargetType,
)
from .autophagy import (
    MutationType,
    SkillRuleAutophagy,
    StagedMutation,
)
from .apoptotic_gate import (
    ApoptoticVerdict,
    CognitiveApoptoticGate,
)
from .foraging import (
    CognitiveForagingEngine,
    ForageSourceType,
    ForagingPolicy,
    Nutrient,
)
from .organism import (
    AntigravityOrganism,
    GenerationNode,
    OrganismHeartbeatResult,
)

__all__ = [
    "CognitiveMetabolism",
    "EventType",
    "ProceduralMutationCandidate",
    "SessionEvent",
    "TargetType",
    "MutationType",
    "SkillRuleAutophagy",
    "StagedMutation",
    "ApoptoticVerdict",
    "CognitiveApoptoticGate",
    "CognitiveForagingEngine",
    "ForageSourceType",
    "ForagingPolicy",
    "Nutrient",
    "AntigravityOrganism",
    "GenerationNode",
    "OrganismHeartbeatResult",
]
