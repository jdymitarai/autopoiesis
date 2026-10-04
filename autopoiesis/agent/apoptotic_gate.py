"""
Cognitive Apoptotic Gate (Immune System) for Antigravity.

Guarantees non-hallucinatory recursive self-mutation. Any mutation to
Antigravity's instructions, rules, or skills must pass strict immune validation:
- Chesterton's fence invariant checks
- YAML frontmatter and Markdown syntax verification
- Python AST syntax checking
- Anti-degradation, anti-truncation, and anti-hallucination checks
Instant rejection (apoptosis) and atomic rollback on any violation.
"""

from __future__ import annotations

import ast
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .autophagy import StagedMutation


@dataclass
class ApoptoticVerdict:
    """Immune system verdict emitted by the Cognitive Apoptotic Gate."""
    approved: bool
    mutation_id: str
    target_path: str
    rejection_reason: Optional[str] = None
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "mutation_id": self.mutation_id,
            "target_path": self.target_path,
            "rejection_reason": self.rejection_reason,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApoptoticVerdict:
        return cls(**data)


class CognitiveApoptoticGate:
    """
    Deterministic Immune Gate protecting Antigravity from degradation,
    hallucinatory drift, or accidental deletion of critical safety constraints.
    """

    # Essential invariants that must NEVER be deleted from AGENTS.md (Chesterton's fence)
    ESSENTIAL_RULE_INVARIANTS = [
        "Strict Repository PR Concurrency Limit Rule",
        "Defensive Engineering & Surgical Changes Rule",
        "Autonomous Subagent Delegation Rule",
    ]

    ESSENTIAL_KEYWORD_INVARIANTS = [
        "Surgical Precision",
        "Chesterton's Fence",
        "Pre-flight Self-Verification Loop",
    ]

    # Forbidden placeholder patterns that indicate incomplete or hallucinated code
    FORBIDDEN_PATTERNS = [
        r"TODO:\s*implement",
        r"\[INSERT CODE HERE\]",
        r"<<REPLACE_ME>>",
        r"pass\s*#\s*placeholder",
        r"AI generated template",
    ]

    def __init__(
        self,
        enforce_chesterton: bool = True,
        max_expansion_ratio: float = 4.0,
        min_retention_ratio: float = 0.5,
    ) -> None:
        self.enforce_chesterton = enforce_chesterton
        self.max_expansion_ratio = max_expansion_ratio
        self.min_retention_ratio = min_retention_ratio

    def verify(self, staged: StagedMutation) -> ApoptoticVerdict:
        """
        Run the complete immune validation suite against a staged mutation.
        Returns ApoptoticVerdict indicating approval or rejection.
        """
        passed: List[str] = []
        failed: List[str] = []

        target_file = Path(staged.target_path)
        filename = target_file.name.lower()
        mutated = staged.mutated_content
        original = staged.original_content

        # -----------------------------------------------------------------
        # 1. Non-empty Content Check
        # -----------------------------------------------------------------
        if not mutated.strip():
            return self._reject(
                staged,
                "EMPTY_CONTENT: Mutation resulted in empty content.",
                passed,
                ["non_empty_content"],
            )
        passed.append("non_empty_content")

        # -----------------------------------------------------------------
        # 2. Forbidden Placeholder / Hallucination Detection
        # -----------------------------------------------------------------
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, mutated, re.IGNORECASE):
                return self._reject(
                    staged,
                    f"HALLUCINATION_DETECTED: Mutation contains forbidden placeholder pattern: '{pattern}'",
                    passed,
                    ["anti_hallucination_pattern"],
                )
        passed.append("anti_hallucination_pattern")

        # -----------------------------------------------------------------
        # 3. File Size & Truncation Defense
        # -----------------------------------------------------------------
        if original.strip():
            orig_len = len(original)
            mut_len = len(mutated)

            # Prevent catastrophic accidental truncation
            if orig_len >= 100 and mut_len < orig_len * self.min_retention_ratio:
                return self._reject(
                    staged,
                    f"ACCIDENTAL_TRUNCATION: File shrank drastically from {orig_len} to {mut_len} chars "
                    f"(retention ratio {mut_len/orig_len:.2f} < {self.min_retention_ratio})",
                    passed,
                    ["anti_truncation_check"],
                )

            # Prevent sudden uncontrolled file bloat
            if orig_len >= 100 and mut_len > orig_len * self.max_expansion_ratio:
                return self._reject(
                    staged,
                    f"PROMPT_BLOAT_DETECTED: File size exploded from {orig_len} to {mut_len} chars "
                    f"(expansion ratio {mut_len/orig_len:.2f} > {self.max_expansion_ratio})",
                    passed,
                    ["anti_bloat_check"],
                )
        passed.append("size_boundary_check")

        # -----------------------------------------------------------------
        # 4. Chesterton's Fence & Core Invariant Check (for Rules / AGENTS.md)
        # -----------------------------------------------------------------
        if filename.endswith(".md") and "agent" in filename:
            if self.enforce_chesterton:
                for rule_name in self.ESSENTIAL_RULE_INVARIANTS:
                    if rule_name not in mutated:
                        return self._reject(
                            staged,
                            f"CHESTERTon_FENCE_VIOLATION: Crucial rule section '{rule_name}' was removed or altered.",
                            passed,
                            ["chesterton_rule_invariants"],
                        )

                for kw in self.ESSENTIAL_KEYWORD_INVARIANTS:
                    if kw not in mutated:
                        return self._reject(
                            staged,
                            f"CHESTERTon_FENCE_VIOLATION: Essential engineering keyword '{kw}' was deleted.",
                            passed,
                            ["chesterton_keyword_invariants"],
                        )
                passed.append("chesterton_fence_invariants")

        # -----------------------------------------------------------------
        # 5. Skill File Structure & Frontmatter Validation
        # -----------------------------------------------------------------
        if filename == "skill.md" or (staged.target_type == "SKILL" and filename.endswith(".md")):
            fm_result, fm_reason = self._validate_skill_frontmatter(mutated)
            if not fm_result:
                return self._reject(
                    staged,
                    f"MALFORMED_SKILL_FRONTMATTER: {fm_reason}",
                    passed,
                    ["skill_frontmatter_syntax"],
                )
            passed.append("skill_frontmatter_syntax")

        # -----------------------------------------------------------------
        # 6. Python AST Syntax Validation (if script or python file)
        # -----------------------------------------------------------------
        if filename.endswith(".py"):
            try:
                ast.parse(mutated)
                passed.append("python_ast_syntax")
            except SyntaxError as syn_err:
                return self._reject(
                    staged,
                    f"PYTHON_SYNTAX_ERROR at line {syn_err.lineno}: {syn_err.msg}",
                    passed,
                    ["python_ast_syntax"],
                )

        # All checks passed!
        return ApoptoticVerdict(
            approved=True,
            mutation_id=staged.mutation_id,
            target_path=staged.target_path,
            checks_passed=passed,
            checks_failed=[],
        )

    def verify_all(
        self, staged_list: List[StagedMutation]
    ) -> Tuple[List[StagedMutation], List[ApoptoticVerdict]]:
        """Verify multiple staged mutations, segregating approved from rejected."""
        approved_mutations: List[StagedMutation] = []
        verdicts: List[ApoptoticVerdict] = []

        for staged in staged_list:
            verdict = self.verify(staged)
            verdicts.append(verdict)
            if verdict.approved:
                approved_mutations.append(staged)

        return approved_mutations, verdicts

    def rollback(self, backup_snapshot: Dict[str, str]) -> bool:
        """
        Atomically rollback mutated files to their original baseline contents.
        Returns True if rollback was successful.
        """
        try:
            for file_path, original_content in backup_snapshot.items():
                p = Path(file_path)
                if not original_content:
                    if p.exists():
                        p.unlink()
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(original_content, encoding="utf-8")
            return True
        except Exception:
            return False

    def _validate_skill_frontmatter(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validates that SKILL.md adheres to the standard YAML frontmatter specification."""
        stripped = content.lstrip()
        lines = stripped.splitlines()
        if not lines or lines[0].strip() != "---":
            return False, "Missing opening '---' frontmatter boundary delimiter"

        closing_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                closing_index = i
                break

        if closing_index == -1:
            return False, "Missing closing '---' frontmatter boundary delimiter"

        frontmatter_text = "\n".join(lines[1:closing_index])
        try:
            parsed = yaml.safe_load(frontmatter_text)
            if not isinstance(parsed, dict):
                return False, "Frontmatter YAML did not parse to a dictionary"
        except Exception as e:
            return False, f"YAML parse error: {e}"

        if "name" not in parsed or not str(parsed["name"]).strip():
            return False, "Frontmatter missing non-empty 'name' field"

        if "description" not in parsed or not str(parsed["description"]).strip():
            return False, "Frontmatter missing non-empty 'description' field"

        if len(str(parsed["description"]).strip()) < 10:
            return False, "Frontmatter description too short (< 10 characters)"

        # Ensure there is content following the closing frontmatter delimiter
        remaining_content = "\n".join(lines[closing_index + 1 :]).strip()
        if not remaining_content:
            return False, "SKILL.md has empty markdown body after frontmatter"

        return True, None

    def _reject(
        self,
        staged: StagedMutation,
        reason: str,
        passed: List[str],
        failed: List[str],
    ) -> ApoptoticVerdict:
        return ApoptoticVerdict(
            approved=False,
            mutation_id=staged.mutation_id,
            target_path=staged.target_path,
            rejection_reason=reason,
            checks_passed=passed,
            checks_failed=failed,
        )
