from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from autopr_agent.formatting import normalize_diff_paths, relative_to_repo
from autopr_agent.models import JudgeResult, RunState
from autopr_agent.providers.openai_compatible import ProviderConfigurationError


class PatchJudge(Protocol):
    name: str

    def judge(self, state: RunState, checklist: dict[str, bool], issues: list[str]) -> JudgeResult:
        ...


def build_judge_payload(state: RunState, checklist: dict[str, bool], issues: list[str]) -> dict[str, Any]:
    patch_file = None
    test_file = None
    patch_reason = None
    if state.patch_plan:
        patch_file = relative_to_repo(state.patch_plan.path, state.repo_path)
        patch_reason = state.patch_plan.reason
    if state.test_plan:
        test_file = relative_to_repo(state.test_plan.path, state.repo_path)
    return {
        "issue": state.issue_text,
        "patch_file": patch_file,
        "test_file": test_file,
        "patch_applied": state.patch_applied,
        "patch_changed_lines": state.patch_changed_lines,
        "patch_reason": patch_reason,
        "patch_diff": normalize_diff_paths(state.patch_diff, state.repo_path),
        "regression_failed_before_patch": bool(
            state.verification_before is not None and not state.verification_before.passed
        ),
        "tests_passed_after_patch": bool(
            state.verification_after is not None and state.verification_after.passed
        ),
        "checklist": checklist,
        "deterministic_review_issues": issues,
    }


@dataclass
class HeuristicPatchJudge:
    name: str = "heuristic-judge"

    def judge(self, state: RunState, checklist: dict[str, bool], issues: list[str]) -> JudgeResult:
        score = 100
        score -= 20 * sum(1 for passed in checklist.values() if not passed)
        if state.verification_before is None or state.verification_before.passed:
            score -= 15
        if state.verification_after is None or not state.verification_after.passed:
            score -= 30
        score = max(score, 0)
        approved = score >= 80 and not issues
        rationale = (
            "Patch is approved because it targets source code, includes a regression test, "
            "fails before the patch, passes after the patch, and remains minimal."
            if approved
            else "Patch needs attention because one or more validation, targeting, or minimality checks failed."
        )
        return JudgeResult(
            provider=self.name,
            approved=approved,
            score=score,
            rationale=rationale,
            concerns=list(issues),
        )


@dataclass
class OpenAICompatibleJudge:
    model: str
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1/chat/completions"
    timeout_seconds: int = 60
    name: str = "openai-compatible-judge"

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderConfigurationError(
                f"Missing {self.api_key_env}. Use HeuristicPatchJudge for offline runs."
            )
        return key

    def _chat_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an LLM-as-Judge reviewer for code repair PR candidates. "
                        "Return JSON with approved boolean, score integer 0-100, rationale string, "
                        "and concerns list of strings. Judge correctness, minimality, source targeting, "
                        "test quality, and verification evidence."
                    ),
                },
                {"role": "user", "content": json.dumps(payload)},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return json.loads(data["choices"][0]["message"]["content"])

    def judge(self, state: RunState, checklist: dict[str, bool], issues: list[str]) -> JudgeResult:
        data = self._chat_json(build_judge_payload(state, checklist, issues))
        return JudgeResult(
            provider=self.name,
            approved=bool(data["approved"]),
            score=int(data["score"]),
            rationale=str(data["rationale"]),
            concerns=list(data.get("concerns", [])),
        )
