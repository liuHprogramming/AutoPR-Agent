from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autopr_agent.models import IssueAnalysis, PatchPlan, SuspiciousSymbol, TestPlan


class ProviderConfigurationError(RuntimeError):
    pass


@dataclass
class OpenAICompatibleProvider:
    """Minimal OpenAI-compatible chat-completions adapter.

    This scaffold is intentionally small and dependency-free. It expects a model
    endpoint that returns JSON content matching the requested schema. The local
    heuristic provider remains the default for tests and offline demos.
    """

    model: str
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1/chat/completions"
    timeout_seconds: int = 60

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ProviderConfigurationError(
                f"Missing {self.api_key_env}. Use LocalHeuristicModel for offline runs."
            )
        return key

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)

    def analyze_issue(self, issue_text: str) -> IssueAnalysis:
        data = self._chat_json(
            "Return JSON with title, expected_behavior, observed_behavior, and keywords.",
            issue_text,
        )
        return IssueAnalysis(
            title=data["title"],
            expected_behavior=data["expected_behavior"],
            observed_behavior=data["observed_behavior"],
            keywords=list(data["keywords"]),
        )

    def draft_test(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> TestPlan:
        data = self._chat_json(
            "Return JSON with path, content, and command for a unittest regression test.",
            json.dumps(
                {
                    "analysis": analysis.__dict__,
                    "symbol": {
                        "path": str(symbol.path),
                        "name": symbol.name,
                        "line": symbol.line,
                        "reason": symbol.reason,
                    },
                }
            ),
        )
        return TestPlan(
            path=Path(data["path"]),
            content=data["content"],
            command=list(data["command"]),
        )

    def draft_patch(self, analysis: IssueAnalysis, symbol: SuspiciousSymbol) -> PatchPlan:
        data = self._chat_json(
            "Return JSON with path, original, replacement, and reason for a minimal patch.",
            json.dumps(
                {
                    "analysis": analysis.__dict__,
                    "symbol": {
                        "path": str(symbol.path),
                        "name": symbol.name,
                        "line": symbol.line,
                        "reason": symbol.reason,
                    },
                }
            ),
        )
        return PatchPlan(
            path=Path(data["path"]),
            original=data["original"],
            replacement=data["replacement"],
            reason=data["reason"],
        )
