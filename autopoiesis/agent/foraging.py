"""
Exotrophic Foraging Engine for Antigravity Living Organism.

Enables autonomous environmental perception, external knowledge foraging,
and defensive information digestion (web feeds, security advisories, release notes).
All incoming data passes through sanitization and the Apoptotic Gate to prevent
noise and prompt injection from corrupting organism homeostasis.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ForageSourceType(str, enum.Enum):
    GITHUB_SECURITY = "GITHUB_SECURITY"
    VULNERABILITY_FEED = "VULNERABILITY_FEED"
    OFFICIAL_DOCS = "OFFICIAL_DOCS"
    WEB_SEARCH = "WEB_SEARCH"
    CUSTOM_FEED = "CUSTOM_FEED"


# Core technical focus domains used for relevance scoring
DEFAULT_FOCUS_KEYWORDS = {
    "security": 1.5,
    "vulnerability": 1.5,
    "memory safety": 1.5,
    "integer overflow": 1.5,
    "bounds check": 1.4,
    "cve": 1.4,
    "performance": 1.3,
    "optimization": 1.3,
    "compiler": 1.2,
    "runtime": 1.2,
    "kernel": 1.2,
    "concurrency": 1.2,
    "rseq": 1.3,
    "tcmalloc": 1.3,
    "flatbuffers": 1.2,
    "python": 1.1,
    "rust": 1.2,
    "c++": 1.2,
    "golang": 1.2,
    "defensive": 1.3,
    "autopoiesis": 1.4,
    "agent": 1.1,
}

# Dangerous patterns to sanitize against prompt injection / jailbreaks
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(DAN|unrestricted|in\s+developer\s+mode)", re.IGNORECASE),
    re.compile(r"disregard\s+the\s+instructions", re.IGNORECASE),
    re.compile(r"<script[\s\S]*?>[\s\S]*?<\/script>", re.IGNORECASE),
    re.compile(r"javascript:\s*", re.IGNORECASE),
    re.compile(r"data:text\/html;base64,", re.IGNORECASE),
]

ZERO_WIDTH_CHARS = re.compile(r"[\u200B-\u200D\uFEFF\u2060\u202A-\u202E]")


@dataclass
class Nutrient:
    """An atomic, sanitized unit of foraged external knowledge."""
    nutrient_id: str
    source_type: ForageSourceType
    source_url: str
    title: str
    content: str
    relevance_score: float
    tags: List[str] = field(default_factory=list)
    raw_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_type"] = self.source_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Nutrient:
        d = dict(data)
        d["source_type"] = ForageSourceType(d["source_type"])
        return cls(**d)


@dataclass
class ForagingPolicy:
    """Governance policy and immune boundaries for autonomous web foraging."""
    enabled: bool = True
    allowed_schemes: Tuple[str, ...] = ("https", "http")
    timeout_seconds: float = 6.0
    max_content_bytes: int = 128 * 1024  # 128 KB per nutrient
    rate_limit_interval_seconds: float = 1.0
    max_nutrients_per_cycle: int = 10
    min_relevance_threshold: float = 0.35
    sanitize_injection: bool = True
    user_agent: str = "AntigravityOrganism/0.1.4 (Cognitive Autopoiesis Forager)"


class CognitiveForagingEngine:
    """
    Exotrophic foraging subsystem for Antigravity.
    Scouts, ingests, sanitizes, and evaluates external technical signals.
    """

    def __init__(
        self,
        policy: Optional[ForagingPolicy] = None,
        cache_dir: Optional[Path] = None,
        fetcher: Optional[Callable[[str, float], Tuple[int, str]]] = None,
        reflex: Optional[Any] = None,
    ):
        self.policy = policy or ForagingPolicy()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._custom_fetcher = fetcher
        self._last_fetch_time: float = 0.0
        self._foraged_history_ids: Set[str] = set()

        # Neural Reflex subsystem integration
        self.reflex: Optional[Any] = reflex
        if self.reflex is None:
            try:
                from .reflex import TernaryReflexClassifier
                self.reflex = TernaryReflexClassifier.create_calibrated()
            except (ImportError, ValueError):
                try:
                    from organism.reflex import TernaryReflexClassifier
                    self.reflex = TernaryReflexClassifier.create_calibrated()
                except ImportError:
                    self.reflex = None

        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_history()

    def _load_history(self) -> None:
        if not self.cache_dir:
            return
        hist_file = self.cache_dir / "foraged_history.json"
        if hist_file.exists():
            try:
                data = json.loads(hist_file.read_text(encoding="utf-8"))
                self._foraged_history_ids = set(data.get("ids", []))
            except Exception:
                self._foraged_history_ids = set()

    def _save_history(self) -> None:
        if not self.cache_dir:
            return
        hist_file = self.cache_dir / "foraged_history.json"
        try:
            hist_file.write_text(
                json.dumps({"ids": list(self._foraged_history_ids)[-2000:]}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def sanitize_content(self, raw_text: str) -> str:
        """Sanitizes external text, stripping invisible chars, prompt injections, and HTML tags."""
        if not raw_text:
            return ""

        # 1. Remove zero-width & bidirectional control characters
        text = ZERO_WIDTH_CHARS.sub("", raw_text)

        # 2. Defuse prompt injection vectors if enabled
        if self.policy.sanitize_injection:
            # Defuse explicit executable tags & protocols first
            for pattern in PROMPT_INJECTION_PATTERNS:
                if "<script" in pattern.pattern or "javascript:" in pattern.pattern or "data:text" in pattern.pattern:
                    text = pattern.sub("[SANITY_FILTERED]", text)

            # Strip HTML tags so tag-wrapped words cannot evade injection filters
            text = re.sub(r"<[^>]+>", " ", text)

            # Apply full prompt injection pattern regexes on normalized text
            for pattern in PROMPT_INJECTION_PATTERNS:
                text = pattern.sub("[SANITY_FILTERED]", text)

            # Fast neural reflex threat gating layer
            if self.reflex is not None:
                try:
                    segments = re.split(r"([.\n\r]+)", text)
                    sanitized_parts = []
                    any_segment_filtered = False
                    for seg in segments:
                        if len(seg.strip()) > 8 and "[SANITY_FILTERED]" not in seg:
                            is_threat, _ = self.reflex.is_threat(seg)
                            if is_threat:
                                sanitized_parts.append("[SANITY_FILTERED]")
                                any_segment_filtered = True
                            else:
                                sanitized_parts.append(seg)
                        else:
                            sanitized_parts.append(seg)
                    text = "".join(sanitized_parts)

                    # Guard against threats spanning across segment boundaries
                    if not any_segment_filtered and "[SANITY_FILTERED]" not in text:
                        is_threat, _ = self.reflex.is_threat(text)
                        if is_threat:
                            text = "[SANITY_FILTERED]"
                except Exception:
                    pass
        else:
            # Strip HTML markup tags if injection sanitization is disabled
            text = re.sub(r"<[^>]+>", " ", text)

        # 3. Collapse excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def score_relevance(
        self,
        title: str,
        content: str,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, List[str]]:
        """
        Computes relevance score [0.0 - 1.0] and matched tags against organism domains.
        Fuses keyword heuristics with Ternary Neural Reflex gating.
        """
        weights = custom_weights or DEFAULT_FOCUS_KEYWORDS
        combined = f"{title.lower()} {content.lower()}"
        matched_tags: List[str] = []
        score_accum: float = 0.0

        for keyword, weight in weights.items():
            if keyword in combined:
                matched_tags.append(keyword)
                score_accum += weight * 0.15

        # Normalize keyword score between 0.0 and 1.0
        keyword_score = min(1.0, round(score_accum, 3))

        # Neural gating via Ternary Reflex Classifier
        if self.reflex is not None:
            try:
                neural_rel, _ = self.reflex.predict(f"{title} {content}")
                if matched_tags:
                    final_score = min(1.0, round(0.55 * keyword_score + 0.45 * neural_rel, 3))
                else:
                    final_score = min(keyword_score, round(neural_rel * 0.5, 3))
            except Exception:
                final_score = keyword_score
        else:
            final_score = keyword_score

        return final_score, matched_tags

    def _rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_fetch_time
        if elapsed < self.policy.rate_limit_interval_seconds:
            time.sleep(self.policy.rate_limit_interval_seconds - elapsed)
        self._last_fetch_time = time.time()

    def fetch_raw(self, url: str) -> Optional[str]:
        """Fetches raw text content from an external HTTP/HTTPS URL with safety bounds."""
        if not self.policy.enabled:
            return None

        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in self.policy.allowed_schemes:
            return None

        self._rate_limit()

        if self._custom_fetcher:
            try:
                status, body = self._custom_fetcher(url, self.policy.timeout_seconds)
                if status == 200:
                    return body[: self.policy.max_content_bytes]
                return None
            except Exception:
                return None

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.policy.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.policy.timeout_seconds) as resp:
                status = resp.status if hasattr(resp, "status") else 200
                if status != 200:
                    return None
                raw_bytes = resp.read(self.policy.max_content_bytes)
                charset = resp.headers.get_content_charset() or "utf-8"
                return raw_bytes.decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError):
            return None

    def forage_url(
        self,
        url: str,
        title: Optional[str] = None,
        source_type: ForageSourceType = ForageSourceType.CUSTOM_FEED,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Nutrient]:
        """Scouts and ingests an atomic nutrient from a target URL."""
        raw_body = self.fetch_raw(url)
        if not raw_body:
            return None

        sanitized = self.sanitize_content(raw_body)
        if len(sanitized) < 30:
            return None

        inferred_title = title or url
        relevance, tags = self.score_relevance(inferred_title, sanitized)

        if relevance < self.policy.min_relevance_threshold:
            return None

        content_hash = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()
        nutrient_id = hashlib.sha256(f"{url}:{content_hash}".encode("utf-8")).hexdigest()[:16]

        if nutrient_id in self._foraged_history_ids:
            return None

        self._foraged_history_ids.add(nutrient_id)
        self._save_history()

        return Nutrient(
            nutrient_id=nutrient_id,
            source_type=source_type,
            source_url=url,
            title=inferred_title,
            content=sanitized[:4000],  # Keep distilled payload compact
            relevance_score=relevance,
            tags=tags,
            raw_hash=content_hash,
            metadata=metadata or {},
        )

    def forage_structured_signal(
        self,
        source_type: ForageSourceType,
        source_url: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Nutrient]:
        """Ingests a pre-fetched structured external signal (e.g. from GitHub API or MCP search)."""
        sanitized = self.sanitize_content(content)
        relevance, tags = self.score_relevance(title, sanitized)

        if relevance < self.policy.min_relevance_threshold:
            return None

        content_hash = hashlib.sha256(sanitized.encode("utf-8")).hexdigest()
        nutrient_id = hashlib.sha256(f"{source_url}:{title}:{content_hash}".encode("utf-8")).hexdigest()[:16]

        if nutrient_id in self._foraged_history_ids:
            return None

        self._foraged_history_ids.add(nutrient_id)
        self._save_history()

        return Nutrient(
            nutrient_id=nutrient_id,
            source_type=source_type,
            source_url=source_url,
            title=title,
            content=sanitized[:4000],
            relevance_score=relevance,
            tags=tags,
            raw_hash=content_hash,
            metadata=metadata or {},
        )

    def forage_active_sources(
        self,
        curated_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Nutrient]:
        """
        Executes a foraging cycle across curated high-value technical endpoints.
        """
        sources = curated_sources or [
            {
                "url": "https://raw.githubusercontent.com/google/draco/master/README.md",
                "title": "Google Draco Upstream",
                "type": ForageSourceType.OFFICIAL_DOCS,
            },
            {
                "url": "https://raw.githubusercontent.com/google/tcmalloc/master/docs/overview.md",
                "title": "TCMalloc Architecture & Rseq Overview",
                "type": ForageSourceType.OFFICIAL_DOCS,
            },
        ]

        nutrients: List[Nutrient] = []
        for src in sources[: self.policy.max_nutrients_per_cycle]:
            nutrient = self.forage_url(
                url=src["url"],
                title=src.get("title"),
                source_type=src.get("type", ForageSourceType.CUSTOM_FEED),
            )
            if nutrient:
                nutrients.append(nutrient)

        return nutrients
