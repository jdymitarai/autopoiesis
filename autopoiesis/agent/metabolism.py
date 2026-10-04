"""
Cognitive Metabolism Subsystem for Antigravity.

Digests session interactions, coding feedback, tool failures, and error recoveries
into permanent procedural mutations, defensive heuristics, and skill candidates.
"""

from __future__ import annotations

import enum
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class EventType(str, enum.Enum):
    USER_FEEDBACK = "USER_FEEDBACK"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    TOOL_FAILURE = "TOOL_FAILURE"
    SUCCESSFUL_PATCH = "SUCCESSFUL_PATCH"
    PERFORMANCE_OBSERVATION = "PERFORMANCE_OBSERVATION"


class TargetType(str, enum.Enum):
    SKILL = "SKILL"
    RULE = "RULE"
    INSTRUCTION = "INSTRUCTION"


@dataclass
class SessionEvent:
    """An atomic session interaction or observation."""
    event_id: str
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "session"

    @classmethod
    def create(
        cls,
        event_type: EventType | str,
        payload: Dict[str, Any],
        source: str = "session",
        event_id: Optional[str] = None,
    ) -> SessionEvent:
        if isinstance(event_type, str):
            event_type = EventType(event_type)
        ts = time.time()
        if not event_id:
            payload_repr = json.dumps(payload, sort_keys=True, default=str)
            raw = f"{event_type.value}:{ts}:{payload_repr}"
            event_id = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return cls(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            timestamp=ts,
            source=source,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionEvent:
        data_copy = dict(data)
        data_copy["event_type"] = EventType(data_copy["event_type"])
        return cls(**data_copy)


@dataclass
class ProceduralMutationCandidate:
    """A digested candidate mutation ready for autophagy and apoptotic validation."""
    candidate_id: str
    target_type: TargetType
    target_name: str
    mutation_type: str  # ADD_RULE, UPDATE_RULE, CREATE_SKILL, UPDATE_SKILL, DEFENSIVE_HEURISTIC
    title: str
    content: str
    rationale: str
    confidence: float  # 0.0 to 1.0
    source_events: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @classmethod
    def create(
        cls,
        target_type: TargetType | str,
        target_name: str,
        mutation_type: str,
        title: str,
        content: str,
        rationale: str,
        confidence: float,
        source_events: Optional[List[str]] = None,
    ) -> ProceduralMutationCandidate:
        if isinstance(target_type, str):
            target_type = TargetType(target_type)
        src = source_events or []
        hasher = hashlib.sha256()
        hasher.update(target_type.value.encode("utf-8"))
        hasher.update(target_name.encode("utf-8"))
        hasher.update(mutation_type.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        hasher.update("".join(src).encode("utf-8"))
        cand_id = hasher.hexdigest()[:16]
        return cls(
            candidate_id=cand_id,
            target_type=target_type,
            target_name=target_name,
            mutation_type=mutation_type,
            title=title,
            content=content,
            rationale=rationale,
            confidence=max(0.0, min(1.0, confidence)),
            source_events=src,
            timestamp=time.time(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "target_type": self.target_type.value,
            "target_name": self.target_name,
            "mutation_type": self.mutation_type,
            "title": self.title,
            "content": self.content,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "source_events": self.source_events,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProceduralMutationCandidate:
        data_copy = dict(data)
        data_copy["target_type"] = TargetType(data_copy["target_type"])
        return cls(**data_copy)


class CognitiveMetabolism:
    """
    Cognitive Metabolic engine. Ingests session events and extracts
    reusable procedural heuristics and skill candidates.
    """

    def __init__(self, state_dir: Optional[Path] = None) -> None:
        self.state_dir = Path(state_dir) if state_dir else None
        self.events: List[SessionEvent] = []
        self.digested_event_ids: set[str] = set()
        self.extracted_candidates: List[ProceduralMutationCandidate] = []
        if self.state_dir:
            self._load_state()

    def ingest_event(self, event: SessionEvent) -> None:
        """Ingest a single event into the metabolic pool."""
        if any(e.event_id == event.event_id for e in self.events):
            return  # Idempotent: avoid duplicates
        self.events.append(event)
        self._persist_state()

    def ingest_batch(self, events: List[SessionEvent]) -> None:
        """Ingest a batch of events."""
        for ev in events:
            self.ingest_event(ev)

    def get_pending_events(self) -> List[SessionEvent]:
        """Return events that have not been digested yet."""
        return [e for e in self.events if e.event_id not in self.digested_event_ids]

    def digest(self, min_confidence: float = 0.5) -> List[ProceduralMutationCandidate]:
        """
        Digest pending events into reusable procedural mutation candidates.
        Only returns candidates with confidence >= min_confidence.
        """
        pending = self.get_pending_events()
        if not pending:
            return []

        new_candidates: List[ProceduralMutationCandidate] = []

        # 1. Digest User Feedback
        user_feedback_events = [e for e in pending if e.event_type == EventType.USER_FEEDBACK]
        for ev in user_feedback_events:
            cand = self._digest_user_feedback(ev)
            if cand and cand.confidence >= min_confidence:
                new_candidates.append(cand)
                self.digested_event_ids.add(ev.event_id)

        # 2. Digest Error Recoveries & Tool Failures
        error_events = [e for e in pending if e.event_type in (EventType.ERROR_RECOVERY, EventType.TOOL_FAILURE)]
        for ev in error_events:
            cand = self._digest_error_event(ev)
            if cand and cand.confidence >= min_confidence:
                new_candidates.append(cand)
                self.digested_event_ids.add(ev.event_id)

        # 3. Digest Successful Patches & Performance Observations
        patch_events = [e for e in pending if e.event_type in (EventType.SUCCESSFUL_PATCH, EventType.PERFORMANCE_OBSERVATION)]
        for ev in patch_events:
            cand = self._digest_patch_event(ev)
            if cand and cand.confidence >= min_confidence:
                new_candidates.append(cand)
                self.digested_event_ids.add(ev.event_id)

        # Record and persist
        self.extracted_candidates.extend(new_candidates)
        self._persist_state()
        return new_candidates

    def _digest_user_feedback(self, event: SessionEvent) -> Optional[ProceduralMutationCandidate]:
        payload = event.payload
        rule_text = payload.get("rule") or payload.get("instruction") or payload.get("text", "")
        category = payload.get("category", "General Guidance")
        if not rule_text.strip():
            return None

        # Build clean rule representation
        formatted_content = f"- **Rule**: {rule_text.strip()}"
        confidence = float(payload.get("confidence", 0.9))

        return ProceduralMutationCandidate.create(
            target_type=TargetType.RULE,
            target_name=category,
            mutation_type="ADD_RULE",
            title=f"User Direct Guidance: {category}",
            content=formatted_content,
            rationale=f"Synthesized directly from user interaction feedback event {event.event_id}",
            confidence=confidence,
            source_events=[event.event_id],
        )

    def _digest_error_event(self, event: SessionEvent) -> Optional[ProceduralMutationCandidate]:
        payload = event.payload
        error_msg = payload.get("error") or payload.get("error_message") or ""
        recovery_action = payload.get("recovery_action") or payload.get("fix_applied") or payload.get("resolution") or ""
        context = payload.get("context", "")

        if not recovery_action.strip():
            return None

        # Determine target type: Skill or Rule
        skill_target = payload.get("target_skill")
        if skill_target:
            content = f"### Defensive Recovery Procedure\nWhen encountering `{error_msg}`:\n1. {recovery_action.strip()}\n"
            return ProceduralMutationCandidate.create(
                target_type=TargetType.SKILL,
                target_name=skill_target,
                mutation_type="UPDATE_SKILL",
                title=f"Defensive Recovery for {skill_target}",
                content=content,
                rationale=f"Automated error recovery procedure learned from event {event.event_id}",
                confidence=0.85,
                source_events=[event.event_id],
            )

        # Default to Rule candidate under Defensive Engineering
        content = (
            f"- **Error Defense**: When encountering `{error_msg}` in {context or 'execution'}:\n"
            f"  - Primary Resolution: {recovery_action.strip()}"
        )
        return ProceduralMutationCandidate.create(
            target_type=TargetType.RULE,
            target_name="Defensive Engineering & Surgical Changes Rule",
            mutation_type="ADD_RULE",
            title=f"Error Defense Heuristic: {error_msg[:40]}",
            content=content,
            rationale=f"Learned defensive recovery strategy against recurring failure: {error_msg}",
            confidence=0.8,
            source_events=[event.event_id],
        )

    def _digest_patch_event(self, event: SessionEvent) -> Optional[ProceduralMutationCandidate]:
        payload = event.payload
        skill_name = payload.get("skill_name")
        procedure = payload.get("procedure") or payload.get("solution") or ""
        description = payload.get("description", "Automated procedural optimization")

        if not procedure.strip():
            return None

        if skill_name:
            return ProceduralMutationCandidate.create(
                target_type=TargetType.SKILL,
                target_name=skill_name,
                mutation_type="CREATE_SKILL" if payload.get("is_new_skill") else "UPDATE_SKILL",
                title=f"Procedural Pattern: {skill_name}",
                content=procedure.strip(),
                rationale=description,
                confidence=0.75,
                source_events=[event.event_id],
            )

        return None

    def _persist_state(self) -> None:
        if not self.state_dir:
            return
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.state_dir / "metabolism_state.json"
        data = {
            "events": [e.to_dict() for e in self.events],
            "digested_event_ids": list(self.digested_event_ids),
            "candidates": [c.to_dict() for c in self.extracted_candidates],
        }
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_state(self) -> None:
        if not self.state_dir:
            return
        state_file = self.state_dir / "metabolism_state.json"
        if not state_file.exists():
            return
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.events = [SessionEvent.from_dict(e) for e in data.get("events", [])]
            self.digested_event_ids = set(data.get("digested_event_ids", []))
            self.extracted_candidates = [
                ProceduralMutationCandidate.from_dict(c) for c in data.get("candidates", [])
            ]
        except Exception:
            # Defensive recovery on corrupted state file
            self.events = []
            self.digested_event_ids = set()
            self.extracted_candidates = []
