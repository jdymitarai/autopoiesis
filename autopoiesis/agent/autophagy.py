"""
Skill & Rule Autophagy Subsystem for Antigravity.

Enables Antigravity to autonomously audit, refactor, and self-mutate its own
.agents/skills/ and .agents/AGENTS.md using dual-buffer chromosomal sandboxing.
"""

from __future__ import annotations

import ast
import difflib
import enum
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .metabolism import ProceduralMutationCandidate, TargetType


class MutationType(str, enum.Enum):
    ADD_RULE = "ADD_RULE"
    UPDATE_RULE = "UPDATE_RULE"
    CREATE_SKILL = "CREATE_SKILL"
    UPDATE_SKILL = "UPDATE_SKILL"
    REFACTOR_SKILL = "REFACTOR_SKILL"
    PRUNE_BLOAT = "PRUNE_BLOAT"


@dataclass
class StagedMutation:
    """A mutation prepared in the dual-buffer sandbox prior to apoptotic validation."""
    mutation_id: str
    target_path: str  # String representation for serialization
    target_type: str
    original_content: str
    mutated_content: str
    mutation_type: MutationType
    diff_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        target_path: Path | str,
        target_type: str,
        original_content: str,
        mutated_content: str,
        mutation_type: MutationType | str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StagedMutation:
        if isinstance(mutation_type, str):
            mutation_type = MutationType(mutation_type)
        tpath = str(Path(target_path).resolve())
        meta = metadata or {}

        # Generate readable diff
        orig_lines = original_content.splitlines(keepends=True)
        mut_lines = mutated_content.splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(orig_lines, mut_lines, fromfile="before", tofile="after"))
        diff_summary = diff[:2000] if diff else "No textual change"

        hasher = hashlib.sha256()
        hasher.update(tpath.encode("utf-8"))
        hasher.update(mutated_content.encode("utf-8"))
        hasher.update(mutation_type.value.encode("utf-8"))
        mut_id = hasher.hexdigest()[:16]

        return cls(
            mutation_id=mut_id,
            target_path=tpath,
            target_type=target_type,
            original_content=original_content,
            mutated_content=mutated_content,
            mutation_type=mutation_type,
            diff_summary=diff_summary,
            metadata=meta,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "target_path": self.target_path,
            "target_type": self.target_type,
            "original_content": self.original_content,
            "mutated_content": self.mutated_content,
            "mutation_type": self.mutation_type.value,
            "diff_summary": self.diff_summary,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StagedMutation:
        data_copy = dict(data)
        data_copy["mutation_type"] = MutationType(data_copy["mutation_type"])
        return cls(**data_copy)


class SkillRuleAutophagy:
    """
    Autophagy engine: audits existing skills and rules, eliminates bloat,
    and stages procedural mutations into the dual-buffer pipeline.
    """

    def __init__(self, agents_dir: Path) -> None:
        self.agents_dir = Path(agents_dir).resolve()
        self.skills_dir = self.agents_dir / "skills"
        self.rules_file = self.agents_dir / "AGENTS.md"

    @staticmethod
    def clean_text(text: str, max_consecutive_newlines: int = 2) -> str:
        """Normalize line endings, trim trailing whitespaces, and collapse blank lines."""
        text = text.replace("\r\n", "\n")
        pattern = rf"\n{{{max_consecutive_newlines + 1},}}"
        replacement = "\n" * max_consecutive_newlines
        cleaned = re.sub(pattern, replacement, text)
        cleaned_lines = [line.rstrip() for line in cleaned.splitlines()]
        return "\n".join(cleaned_lines) + "\n"

    def stage_candidate(
        self, candidate: ProceduralMutationCandidate, base_content: Optional[str] = None
    ) -> StagedMutation:
        """Stage a single procedural mutation candidate into the dual-buffer."""
        if candidate.target_type == TargetType.RULE:
            return self._stage_rule_candidate(candidate, base_content=base_content)
        elif candidate.target_type == TargetType.SKILL:
            return self._stage_skill_candidate(candidate, base_content=base_content)
        else:
            # Fallback rule modification
            return self._stage_rule_candidate(candidate, base_content=base_content)

    def _stage_rule_candidate(
        self, candidate: ProceduralMutationCandidate, base_content: Optional[str] = None
    ) -> StagedMutation:
        target_path = self.rules_file
        if base_content is not None:
            original_content = base_content
        elif target_path.exists():
            original_content = target_path.read_text(encoding="utf-8")
        else:
            original_content = ""

        target_section = candidate.target_name.strip()
        new_content_snippet = candidate.content.strip()

        # Idempotency check: if rule is already present in original_content, no-op
        if new_content_snippet in original_content:
            return StagedMutation.create(
                target_path=target_path,
                target_type="RULE",
                original_content=original_content,
                mutated_content=original_content,
                mutation_type=MutationType.UPDATE_RULE,
                metadata={
                    "candidate_id": candidate.candidate_id,
                    "title": candidate.title,
                    "confidence": candidate.confidence,
                    "target_section": target_section,
                    "no_op": True,
                },
            )

        # Check if the section already exists in AGENTS.md
        section_pattern = rf"(##\s+{re.escape(target_section)}[^\n]*\n)"
        match = re.search(section_pattern, original_content)

        if match:
            # Append cleanly into the existing section
            pos = match.end()
            mutated_content = (
                original_content[:pos]
                + f"\n{new_content_snippet}\n"
                + original_content[pos:]
            )
        else:
            # Append as a new section at the end
            separator = "\n\n" if original_content and not original_content.endswith("\n\n") else ""
            mutated_content = (
                original_content
                + f"{separator}## {target_section}\n\n{new_content_snippet}\n"
            )

        return StagedMutation.create(
            target_path=target_path,
            target_type="RULE",
            original_content=original_content,
            mutated_content=mutated_content,
            mutation_type=MutationType.ADD_RULE if not match else MutationType.UPDATE_RULE,
            metadata={
                "candidate_id": candidate.candidate_id,
                "title": candidate.title,
                "confidence": candidate.confidence,
                "target_section": target_section,
            },
        )

    def _stage_skill_candidate(
        self, candidate: ProceduralMutationCandidate, base_content: Optional[str] = None
    ) -> StagedMutation:
        skill_name = candidate.target_name.strip().lower().replace(" ", "-")
        target_skill_dir = self.skills_dir / skill_name
        target_file = target_skill_dir / "SKILL.md"

        if base_content is not None:
            original_content = base_content
        elif target_file.exists():
            original_content = target_file.read_text(encoding="utf-8")
        else:
            original_content = ""

        if original_content:
            # Idempotency check: if procedure is already present in skill
            if candidate.content.strip() in original_content:
                mutated_content = original_content
                mtype = MutationType.UPDATE_SKILL
            else:
                mutated_content = original_content.rstrip() + f"\n\n{candidate.content.strip()}\n"
                mtype = MutationType.UPDATE_SKILL
        else:
            # Synthesize brand new skill with valid frontmatter
            frontmatter = {
                "name": skill_name,
                "description": candidate.rationale or candidate.title,
            }
            yaml_header = yaml.dump(frontmatter, sort_keys=False).strip()
            mutated_content = (
                f"---\n{yaml_header}\n---\n\n"
                f"# {candidate.title}\n\n"
                f"## Procedural Execution\n\n{candidate.content.strip()}\n"
            )
            mtype = MutationType.CREATE_SKILL

        return StagedMutation.create(
            target_path=target_file,
            target_type="SKILL",
            original_content=original_content,
            mutated_content=mutated_content,
            mutation_type=mtype,
            metadata={
                "candidate_id": candidate.candidate_id,
                "skill_name": skill_name,
                "title": candidate.title,
                "confidence": candidate.confidence,
                "no_op": (mutated_content == original_content and bool(original_content)),
            },
        )

    def audit_skills(self) -> List[StagedMutation]:
        """
        Audit all skills in the skills directory for formatting bloat,
        broken frontmatter, or missing docstrings.
        """
        staged: List[StagedMutation] = []
        if not self.skills_dir.exists():
            return staged

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                content = skill_file.read_text(encoding="utf-8")
            except Exception:
                continue

            normalized = self.clean_text(content, max_consecutive_newlines=2)

            if normalized != content:
                staged.append(
                    StagedMutation.create(
                        target_path=skill_file,
                        target_type="SKILL",
                        original_content=content,
                        mutated_content=normalized,
                        mutation_type=MutationType.PRUNE_BLOAT,
                        metadata={"skill": skill_dir.name, "reason": "Whitespace & bloat normalization"},
                    )
                )

        return staged

    def audit_rules(self, base_content: Optional[str] = None) -> List[StagedMutation]:
        """Audit AGENTS.md for formatting bloat or redundant newlines."""
        staged: List[StagedMutation] = []
        if base_content is not None:
            content = base_content
        elif self.rules_file.exists():
            try:
                content = self.rules_file.read_text(encoding="utf-8")
            except Exception:
                return staged
        else:
            return staged

        normalized = self.clean_text(content, max_consecutive_newlines=3)

        if normalized != content:
            staged.append(
                StagedMutation.create(
                    target_path=self.rules_file,
                    target_type="RULE",
                    original_content=content,
                    mutated_content=normalized,
                    mutation_type=MutationType.PRUNE_BLOAT,
                    metadata={"reason": "Rules file formatting normalization"},
                )
            )

        return staged

    def audit_skill_scripts(self) -> List[Dict[str, Any]]:
        """
        Audit python scripts within skills using AST and autopoiesis complexity analysis.
        Identifies deeply nested loop structures and transpilable hotspot candidates.
        """
        findings: List[Dict[str, Any]] = []
        if not self.skills_dir.exists():
            return findings

        # Check if autopoiesis ASTComplexityVisitor is importable
        ast_visitor_cls = None
        try:
            from autopoiesis.core.hotspot import ASTComplexityVisitor
            ast_visitor_cls = ASTComplexityVisitor
        except ImportError:
            pass

        for py_file in self.skills_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                code = py_file.read_text(encoding="utf-8")
                tree = ast.parse(code, filename=str(py_file))
                if ast_visitor_cls:
                    visitor = ast_visitor_cls()
                    visitor.visit(tree)
                    if visitor.max_loop_depth >= 3:
                        findings.append({
                            "file": str(py_file),
                            "issue": f"High loop nesting depth ({visitor.max_loop_depth})",
                            "loop_depth": visitor.max_loop_depth,
                            "arithmetic_ops": visitor.arithmetic_ops,
                            "transpilable": visitor.max_loop_depth >= 1 and visitor.arithmetic_ops >= 1,
                        })
            except Exception:
                continue

        return findings
