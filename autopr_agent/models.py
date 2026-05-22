from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class IssueAnalysis:
    title: str
    expected_behavior: str
    observed_behavior: str
    keywords: list[str]


@dataclass
class SearchResult:
    path: Path
    score: int
    matched_terms: list[str]


@dataclass
class SuspiciousSymbol:
    path: Path
    name: str
    line: int
    reason: str


@dataclass
class TestPlan:
    path: Path
    content: str
    command: list[str]


@dataclass
class PatchPlan:
    path: Path
    original: str
    replacement: str
    reason: str


@dataclass
class VerificationResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class ReviewResult:
    approved: bool
    issues: list[str] = field(default_factory=list)
    checklist: dict[str, bool] = field(default_factory=dict)
    risk_level: str = "low"


@dataclass
class RunState:
    repo_path: Path
    issue_text: str
    analysis: IssueAnalysis | None = None
    search_results: list[SearchResult] = field(default_factory=list)
    suspicious_symbols: list[SuspiciousSymbol] = field(default_factory=list)
    test_plan: TestPlan | None = None
    patch_plan: PatchPlan | None = None
    patch_applied: bool = False
    patch_diff: str = ""
    patch_changed_lines: int = 0
    review: ReviewResult | None = None
    verification_before: VerificationResult | None = None
    verification_after: VerificationResult | None = None
    iterations: int = 0
    events: list[str] = field(default_factory=list)

    def add_event(self, message: str) -> None:
        self.events.append(message)
