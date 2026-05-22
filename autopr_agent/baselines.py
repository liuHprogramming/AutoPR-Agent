from __future__ import annotations

from pathlib import Path

from autopr_agent.agents import ReporterAgent, VerifierAgent
from autopr_agent.llm import LocalHeuristicModel, ModelProvider
from autopr_agent.models import RunState, SearchResult, SuspiciousSymbol
from autopr_agent.tools import RepoTools


class SingleAgentBaseline:
    """A compact all-in-one repair baseline."""

    def __init__(self, repo_path: Path, model: ModelProvider | None = None) -> None:
        self.tools = RepoTools(repo_path)
        self.model = model or LocalHeuristicModel()
        self.verifier = VerifierAgent(self.tools)
        self.reporter = ReporterAgent()

    def run(self, issue_text: str) -> tuple[RunState, str]:
        state = RunState(repo_path=self.tools.repo_path, issue_text=issue_text)
        state.analysis = self.model.analyze_issue(issue_text)
        state.add_event(f"Single-agent baseline analyzed issue: {state.analysis.title}")

        results = self.tools.search_terms(state.analysis.keywords)
        state.search_results = [
            SearchResult(path=path, score=score, matched_terms=matched)
            for path, score, matched in results
        ]
        state.add_event(f"Single-agent baseline found {len(state.search_results)} candidate files")

        if not state.search_results:
            state.add_event("Single-agent baseline stopped: no candidate file")
            return state, self.reporter.run(state)

        target = state.search_results[0]
        functions = self.tools.extract_functions(target.path)
        if not functions:
            state.add_event("Single-agent baseline stopped: no function found")
            return state, self.reporter.run(state)

        chosen = functions[0]
        state.suspicious_symbols = [
            SuspiciousSymbol(
                path=target.path,
                name=chosen.name,
                line=chosen.line,
                reason="Highest-scoring file and first parsed function",
            )
        ]
        state.add_event(f"Single-agent baseline selected `{chosen.name}` in {target.path.name}")

        state.test_plan = self.model.draft_test(state.analysis, state.suspicious_symbols[0])
        self.tools.write_text(state.test_plan.path, state.test_plan.content)
        state.patch_plan = self.model.draft_patch(state.analysis, state.suspicious_symbols[0])
        if state.patch_plan.original:
            result = self.tools.apply_replacement(
                state.patch_plan.path,
                state.patch_plan.original,
                state.patch_plan.replacement,
            )
            state.patch_applied = result.applied
            state.patch_diff = result.diff
            state.patch_changed_lines = result.changed_lines
        state.add_event("Single-agent baseline patched immediately")

        state.verification_after = self.verifier.run_tests(state.test_plan.command)
        state.add_event(
            "Single-agent baseline tests passed"
            if state.verification_after.passed
            else "Single-agent baseline tests failed"
        )
        return state, self.reporter.run(state)

