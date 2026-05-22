from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from autopr_agent.models import IssueAnalysis, PatchPlan, SuspiciousSymbol, TestPlan


class ModelProvider(Protocol):
    def analyze_issue(self, issue_text: str) -> IssueAnalysis:
        ...

    def draft_test(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> TestPlan:
        ...

    def draft_patch(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> PatchPlan:
        ...


@dataclass
class LocalHeuristicModel:
    """Deterministic stand-in for an LLM provider.

    The project architecture treats this as a model adapter. A later provider can
    call OpenAI, Qwen, Claude, or Ollama while keeping the agents unchanged.
    """

    def analyze_issue(self, issue_text: str) -> IssueAnalysis:
        lowered = issue_text.lower()
        keywords = []
        for token in (
            "factorial",
            "fibonacci",
            "divide",
            "sort",
            "parse",
            "normalize_whitespace",
            "whitespace",
            "unique_preserve_order",
            "merge_defaults",
            "defaults",
            "overrides",
            "preserve",
            "order",
        ):
            if token in lowered:
                keywords.append(token)
        if "0" in issue_text:
            keywords.append("0")
        if "space" in lowered or "spaces" in lowered:
            keywords.append("space")
        if "unique" in lowered:
            keywords.append("unique")
        if "default" in lowered or "defaults" in lowered:
            keywords.append("defaults")
        if "override" in lowered or "overrides" in lowered:
            keywords.append("overrides")
        return IssueAnalysis(
            title=issue_text.strip().split(".")[0][:80] or "Bug report",
            expected_behavior="The implementation should match the behavior described by the issue.",
            observed_behavior=issue_text.strip(),
            keywords=keywords or issue_text.lower().split()[:5],
        )

    def draft_test(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> TestPlan:
        if "factorial" in analysis.keywords:
            content = (
                "import unittest\n\n"
                "from src.math_utils import factorial\n\n\n"
                "class TestFactorialRegression(unittest.TestCase):\n"
                "    def test_factorial_zero_returns_one(self) -> None:\n"
                "        self.assertEqual(factorial(0), 1)\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    unittest.main()\n"
            )
            return TestPlan(
                path=symbol.path.parent.parent / "tests" / "test_factorial_regression.py",
                content=content,
                command=["python3", "-m", "unittest", "discover", "tests"],
            )
        if "normalize_whitespace" in analysis.keywords or "whitespace" in analysis.keywords:
            content = (
                "import unittest\n\n"
                "from src.text_utils import normalize_whitespace\n\n\n"
                "class TestWhitespaceRegression(unittest.TestCase):\n"
                "    def test_collapses_repeated_internal_spaces(self) -> None:\n"
                "        self.assertEqual(normalize_whitespace(\"hello   world\"), \"hello world\")\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    unittest.main()\n"
            )
            return TestPlan(
                path=symbol.path.parent.parent / "tests" / "test_whitespace_regression.py",
                content=content,
                command=["python3", "-m", "unittest", "discover", "tests"],
            )
        if "unique_preserve_order" in analysis.keywords or ("preserve" in analysis.keywords and "defaults" not in analysis.keywords):
            content = (
                "import unittest\n\n"
                "from src.list_utils import unique_preserve_order\n\n\n"
                "class TestUniqueOrderRegression(unittest.TestCase):\n"
                "    def test_preserves_first_seen_order(self) -> None:\n"
                "        self.assertEqual(\n"
                "            unique_preserve_order([\"b\", \"a\", \"b\", \"c\", \"a\"]),\n"
                "            [\"b\", \"a\", \"c\"],\n"
                "        )\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    unittest.main()\n"
            )
            return TestPlan(
                path=symbol.path.parent.parent / "tests" / "test_unique_order_regression.py",
                content=content,
                command=["python3", "-m", "unittest", "discover", "tests"],
            )
        if "merge_defaults" in analysis.keywords or "defaults" in analysis.keywords:
            content = (
                "import unittest\n\n"
                "from src.dict_utils import merge_defaults\n\n\n"
                "class TestMergeDefaultsRegression(unittest.TestCase):\n"
                "    def test_preserves_missing_default_keys(self) -> None:\n"
                "        result = merge_defaults(\n"
                "            {\"theme\": \"light\", \"language\": \"en\"},\n"
                "            {\"theme\": \"dark\"},\n"
                "        )\n"
                "        self.assertEqual(result, {\"theme\": \"dark\", \"language\": \"en\"})\n\n\n"
                "if __name__ == \"__main__\":\n"
                "    unittest.main()\n"
            )
            return TestPlan(
                path=symbol.path.parent.parent / "tests" / "test_merge_defaults_regression.py",
                content=content,
                command=["python3", "-m", "unittest", "discover", "tests"],
            )
        content = (
            "import unittest\n\n\n"
            "class TestRegressionPlaceholder(unittest.TestCase):\n"
            "    def test_placeholder_regression(self) -> None:\n"
            "        self.assertTrue(True)\n\n\n"
            "if __name__ == \"__main__\":\n"
            "    unittest.main()\n"
        )
        return TestPlan(
            path=symbol.path.parent.parent / "tests" / "test_regression.py",
            content=content,
            command=["python3", "-m", "unittest", "discover", "tests"],
        )

    def draft_patch(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> PatchPlan:
        if "factorial" in analysis.keywords:
            return PatchPlan(
                path=symbol.path,
                original="if n == 0:\n        return 0",
                replacement="if n == 0:\n        return 1",
                reason="factorial(0) is defined as 1.",
            )
        if "normalize_whitespace" in analysis.keywords or "whitespace" in analysis.keywords:
            return PatchPlan(
                path=symbol.path,
                original="def normalize_whitespace(text: str) -> str:\n    return text.strip()",
                replacement=(
                    "def normalize_whitespace(text: str) -> str:\n"
                    "    return \" \".join(text.split())"
                ),
                reason="Repeated internal whitespace should collapse to a single space.",
            )
        if "unique_preserve_order" in analysis.keywords or ("preserve" in analysis.keywords and "defaults" not in analysis.keywords):
            return PatchPlan(
                path=symbol.path,
                original=(
                    "def unique_preserve_order(items: list[str]) -> list[str]:\n"
                    "    return sorted(set(items))"
                ),
                replacement=(
                    "def unique_preserve_order(items: list[str]) -> list[str]:\n"
                    "    seen = set()\n"
                    "    result = []\n"
                    "    for item in items:\n"
                    "        if item not in seen:\n"
                    "            seen.add(item)\n"
                    "            result.append(item)\n"
                    "    return result"
                ),
                reason="Unique filtering should preserve first-seen order instead of sorting.",
            )
        if "merge_defaults" in analysis.keywords or "defaults" in analysis.keywords:
            return PatchPlan(
                path=symbol.path,
                original=(
                    "def merge_defaults(defaults: dict[str, str], overrides: dict[str, str]) -> dict[str, str]:\n"
                    "    return overrides.copy()"
                ),
                replacement=(
                    "def merge_defaults(defaults: dict[str, str], overrides: dict[str, str]) -> dict[str, str]:\n"
                    "    result = defaults.copy()\n"
                    "    result.update(overrides)\n"
                    "    return result"
                ),
                reason="Defaults should be preserved unless an override replaces them.",
            )
        return PatchPlan(
            path=symbol.path,
            original="",
            replacement="",
            reason="No deterministic patch rule matched this issue.",
        )
