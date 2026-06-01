from __future__ import annotations

from pathlib import Path

from autopr_agent.agents import (
    BugLocalizationAgent,
    CodeSearchAgent,
    IssueUnderstandingAgent,
    PatchAgent,
    ReporterAgent,
    ReviewAgent,
    TestGenerationAgent,
    VerifierAgent,
)
from autopr_agent.llm import LocalHeuristicModel, ModelProvider
from autopr_agent.models import RunState
from autopr_agent.tools import RepoTools


class AutoPRWorkflow:
    def __init__(self, repo_path: Path, model: ModelProvider | None = None) -> None:
        self.tools = RepoTools(repo_path)
        self.model = model or LocalHeuristicModel()
        self.issue_agent = IssueUnderstandingAgent(self.model)
        self.search_agent = CodeSearchAgent(self.tools)
        self.localization_agent = BugLocalizationAgent(self.tools)
        self.test_agent = TestGenerationAgent(self.model, self.tools)
        self.patch_agent = PatchAgent(self.model, self.tools)
        self.review_agent = ReviewAgent()
        self.verifier_agent = VerifierAgent(self.tools)
        self.reporter_agent = ReporterAgent()

    def run(self, issue_text: str) -> tuple[RunState, str]:
        state = RunState(repo_path=self.tools.repo_path, issue_text=issue_text)
        self.issue_agent.run(state)
        self.search_agent.run(state)
        self.localization_agent.run(state)
        self.test_agent.run(state)
        self.verifier_agent.run_before_patch(state)
        self.patch_agent.run(state)
        self.review_agent.run(state)
        self.verifier_agent.run_after_patch(state)
        return state, self.reporter_agent.run(state)

