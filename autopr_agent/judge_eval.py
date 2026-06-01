from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autopr_agent.judge import HeuristicPatchJudge, OpenAICompatibleJudge
from autopr_agent.models import JudgeResult


@dataclass(frozen=True)
class JudgeEvalResult:
    case_id: str
    category: str
    expected_approved: bool
    actual_approved: bool
    score: int
    correct: bool
    rationale: str
    concerns: list[str]


def load_cases(path: Path) -> list[dict[str, Any]]:
    return list(json.loads(path.read_text(encoding="utf-8"))["cases"])


def evaluate_cases(cases: list[dict[str, Any]], judge) -> list[JudgeEvalResult]:
    results: list[JudgeEvalResult] = []
    for case in cases:
        decision: JudgeResult = judge.judge_payload(case["payload"])
        expected = bool(case["expected_approved"])
        results.append(
            JudgeEvalResult(
                case_id=case["id"],
                category=case["category"],
                expected_approved=expected,
                actual_approved=decision.approved,
                score=decision.score,
                correct=decision.approved == expected,
                rationale=decision.rationale,
                concerns=list(decision.concerns),
            )
        )
    return results


def summarize(results: list[JudgeEvalResult]) -> dict[str, int | float]:
    total = len(results)
    correct = sum(result.correct for result in results)
    false_approvals = sum(
        result.actual_approved and not result.expected_approved for result in results
    )
    false_rejections = sum(
        not result.actual_approved and result.expected_approved for result in results
    )
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "false_approvals": false_approvals,
        "false_rejections": false_rejections,
    }


def render_report(provider: str, results: list[JudgeEvalResult]) -> str:
    summary = summarize(results)
    lines = [
        "# AutoPR-Agent Judge Evaluation",
        "",
        "## Scope",
        "This labeled evaluation measures whether a patch-review judge approves valid PR candidates and rejects risky ones. The default report uses an offline deterministic heuristic judge for reproducibility. A live OpenAI-compatible judge can be evaluated with the same cases when an API key is available.",
        "",
        "## Summary",
        f"- provider: {provider}",
        f"- correct decisions: {summary['correct']}/{summary['total']}",
        f"- accuracy: {summary['accuracy']:.1%}",
        f"- false approvals: {summary['false_approvals']}",
        f"- false rejections: {summary['false_rejections']}",
        "",
        "## Case Results",
        "Case | Category | Expected approval | Actual approval | Score | Correct",
        "--- | --- | --- | --- | --- | ---",
    ]
    for result in results:
        lines.append(
            f"{result.case_id} | {result.category} | {result.expected_approved} | "
            f"{result.actual_approved} | {result.score} | {result.correct}"
        )
    lines.extend([
        "",
        "## Interpretation",
        "The heuristic judge intentionally relies on structured validation evidence and review checks. The semantic-mismatch case demonstrates its limitation: a checklist can approve a syntactically small, test-passing patch even when the diff contradicts the issue. The optional LLM judge is intended to evaluate that semantic layer.",
    ])
    return "\n".join(lines) + "\n"


def write_json_report(root: Path, provider: str, results: list[JudgeEvalResult]) -> Path:
    output_dir = root / "runs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"judge-eval-{provider}-{timestamp}.json"
    payload = {
        "created_at_utc": timestamp,
        "provider": provider,
        "summary": summarize(results),
        "results": [asdict(result) for result in results],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def write_markdown_report(root: Path, provider: str, results: list[JudgeEvalResult]) -> Path:
    output_path = root / "docs" / "JUDGE_EVALUATION.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(render_report(provider, results), encoding="utf-8")
    return output_path


def create_judge(provider: str, model: str | None, base_url: str | None, api_key_env: str):
    if provider == "heuristic":
        return HeuristicPatchJudge()
    if not model:
        raise ValueError("--model is required for --provider openai-compatible")
    kwargs = {"model": model, "api_key_env": api_key_env}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAICompatibleJudge(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate AutoPR-Agent patch-review judges")
    parser.add_argument("--provider", choices=["heuristic", "openai-compatible"], default="heuristic")
    parser.add_argument("--model", help="model name for OpenAI-compatible judge evaluation")
    parser.add_argument("--base-url", help="OpenAI-compatible chat completions URL")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--no-json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    cases = load_cases(root / "data" / "judge_eval_cases.json")
    judge = create_judge(args.provider, args.model, args.base_url, args.api_key_env)
    results = evaluate_cases(cases, judge)
    provider = judge.name
    print(render_report(provider, results))
    if not args.no_json:
        print(f"json_report={write_json_report(root, provider, results)}")
    if not args.no_markdown:
        print(f"markdown_report={write_markdown_report(root, provider, results)}")


if __name__ == "__main__":
    main()
