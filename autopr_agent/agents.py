from __future__ import annotations

from autopr_agent.formatting import normalize_diff_paths, relative_to_repo
from autopr_agent.llm import LocalHeuristicModel, ModelProvider
from autopr_agent.models import (
    ReviewResult,
    RunState,
    SearchResult,
    SuspiciousSymbol,
    VerificationResult,
)
from autopr_agent.tools import RepoTools


class IssueUnderstandingAgent:
    def __init__(self, model: ModelProvider) -> None:
        self.model = model

    def run(self, state: RunState) -> None:
        state.analysis = self.model.analyze_issue(state.issue_text)
        state.add_event(f"Issue analyzed: {state.analysis.title}")


class CodeSearchAgent:
    def __init__(self, tools: RepoTools) -> None:
        self.tools = tools

    def run(self, state: RunState) -> None:
        assert state.analysis is not None
        results = self.tools.search_terms(state.analysis.keywords)
        state.search_results = [
            SearchResult(path=path, score=score, matched_terms=matched)
            for path, score, matched in results
        ]
        symbol_count = len(self.tools.build_symbol_index())
        state.add_event(
            f"Code search found {len(state.search_results)} candidate files "
            f"after indexing {symbol_count} symbols"
        )


class BugLocalizationAgent:
    def __init__(self, tools: RepoTools) -> None:
        self.tools = tools

    def _score_symbol(self, symbol, keywords: list[str]) -> tuple[int, list[str]]:
        text = self.tools.read_text(symbol.path).lower()
        name = symbol.name.lower()
        matched = [term for term in keywords if term and term.lower() in text]
        score = len(matched)
        for term in keywords:
            lowered = term.lower()
            if lowered and lowered in name:
                score += 5
        if "tests" in symbol.path.parts:
            score -= 3
        if symbol.kind != "function":
            score -= 1
        return score, matched

    def run(self, state: RunState) -> None:
        assert state.analysis is not None
        ranked_symbols = []
        for symbol in self.tools.build_symbol_index():
            score, matched = self._score_symbol(symbol, state.analysis.keywords)
            if score > 0:
                ranked_symbols.append((score, symbol, matched))
        ranked_symbols.sort(key=lambda item: (-item[0], "tests" in item[1].path.parts, str(item[1].path), item[1].line))
        state.suspicious_symbols = [
            SuspiciousSymbol(
                path=symbol.path,
                name=symbol.name,
                line=symbol.line,
                reason=f"AST symbol score={score}; matched keywords: {', '.join(matched) or 'name-only'}",
            )
            for score, symbol, matched in ranked_symbols
        ]
        state.add_event(f"Localized {len(state.suspicious_symbols)} suspicious symbols via AST symbol ranking")


class TestGenerationAgent:
    def __init__(self, model: ModelProvider, tools: RepoTools) -> None:
        self.model = model
        self.tools = tools

    def run(self, state: RunState) -> None:
        assert state.analysis is not None
        if not state.suspicious_symbols:
            state.add_event("Skipped test generation: no suspicious symbol")
            return
        state.test_plan = self.model.draft_test(state.analysis, state.suspicious_symbols[0])
        self.tools.write_text(state.test_plan.path, state.test_plan.content)
        state.add_event(f"Regression test written: {state.test_plan.path.name}")


class PatchAgent:
    def __init__(self, model: ModelProvider, tools: RepoTools) -> None:
        self.model = model
        self.tools = tools

    def run(self, state: RunState) -> None:
        assert state.analysis is not None
        if not state.suspicious_symbols:
            state.add_event("Skipped patching: no suspicious symbol")
            return
        state.patch_plan = self.model.draft_patch(state.analysis, state.suspicious_symbols[0])
        if not state.patch_plan.original:
            state.add_event("Patch agent could not produce a patch")
            return
        result = self.tools.apply_replacement(
            state.patch_plan.path,
            state.patch_plan.original,
            state.patch_plan.replacement,
        )
        state.patch_applied = result.applied
        state.patch_diff = result.diff
        state.patch_changed_lines = result.changed_lines
        state.add_event(
            f"Patch applied with {result.changed_lines} changed lines"
            if result.applied
            else "Patch failed to apply"
        )


class ReviewAgent:
    def run(self, state: RunState) -> None:
        issues: list[str] = []
        checklist = {
            "patch_generated": state.patch_plan is not None,
            "patch_applied": state.patch_applied,
            "regression_test_generated": state.test_plan is not None,
            "patch_targets_source": bool(
                state.patch_plan is not None and "tests" not in state.patch_plan.path.parts
            ),
            "patch_is_minimal": 0 < state.patch_changed_lines <= 20,
        }
        if state.patch_plan is None:
            issues.append("No patch was generated.")
        elif not state.patch_applied:
            issues.append("Patch did not apply to the selected file.")
        elif "tests" in state.patch_plan.path.parts:
            issues.append("Patch targets a test file instead of source code.")
        elif len(state.patch_plan.replacement) > 1000:
            issues.append("Patch is unexpectedly large for the reported bug.")
        elif state.patch_changed_lines > 20:
            issues.append("Patch changes too many lines for a seeded repair task.")
        if state.test_plan is None:
            issues.append("No regression test was generated.")
        failed_checks = sum(1 for passed in checklist.values() if not passed)
        risk_level = "low" if not issues else "medium" if failed_checks <= 2 else "high"
        state.review = ReviewResult(approved=not issues, issues=issues, checklist=checklist, risk_level=risk_level)
        state.add_event(
            f"Review approved patch with {risk_level} risk"
            if state.review.approved
            else f"Review rejected patch with {risk_level} risk"
        )


class VerifierAgent:
    def __init__(self, tools: RepoTools) -> None:
        self.tools = tools

    def run_tests(self, command: list[str]) -> VerificationResult:
        completed = self.tools.run(command)
        return VerificationResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def run_before_patch(self, state: RunState) -> None:
        if state.test_plan is None:
            return
        state.verification_before = self.run_tests(state.test_plan.command)
        state.add_event(
            "Regression test failed before patch as expected"
            if not state.verification_before.passed
            else "Regression test unexpectedly passed before patch"
        )

    def run_after_patch(self, state: RunState) -> None:
        if state.test_plan is None:
            return
        state.verification_after = self.run_tests(state.test_plan.command)
        state.add_event(
            "Tests passed after patch"
            if state.verification_after.passed
            else "Tests still fail after patch"
        )


class ReporterAgent:
    def run(self, state: RunState) -> str:
        lines = [
            "# AutoPR-Agent Run Summary",
            "",
            f"Issue: {state.issue_text}",
            "",
            "## Agent Trace",
        ]
        lines.extend(f"- {event}" for event in state.events)
        lines.extend(["", "## Result"])
        if state.verification_after and state.verification_after.passed:
            lines.append("Patch candidate validated by regression tests.")
        else:
            lines.append("Patch candidate was not validated.")
        if state.review:
            lines.extend(["", "## Review", f"Risk: {state.review.risk_level}"])
            lines.extend(
                f"- {name}: {passed}" for name, passed in state.review.checklist.items()
            )
            if state.review.issues:
                lines.extend(f"- issue: {issue}" for issue in state.review.issues)
        if state.patch_plan:
            lines.extend(
                [
                    "",
                    "## Patch",
                    f"File: `{relative_to_repo(state.patch_plan.path, state.repo_path)}`",
                    f"Reason: {state.patch_plan.reason}",
                    f"Changed lines: {state.patch_changed_lines}",
                ]
            )
            if state.patch_diff:
                lines.extend(["", "```diff", normalize_diff_paths(state.patch_diff, state.repo_path), "```"])
        return "\n".join(lines)
