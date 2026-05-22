from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from autopr_agent.benchmark import BenchmarkTask, default_tasks
from autopr_agent.llm import LocalHeuristicModel
from autopr_agent.tools import RepoTools


@dataclass(frozen=True)
class RetrievalResult:
    task: str
    strategy: str
    selected_file: str | None
    expected_file: str
    hit: bool


def keyword_top1(task: BenchmarkTask, tools: RepoTools, keywords: list[str]) -> str | None:
    results = tools.search_terms(keywords)
    if not results:
        return None
    return results[0][0].relative_to(tools.repo_path).as_posix()


def ast_symbol_top1(task: BenchmarkTask, tools: RepoTools, keywords: list[str]) -> str | None:
    scored = []
    for symbol in tools.build_symbol_index():
        text = tools.read_text(symbol.path).lower()
        name = symbol.name.lower()
        score = sum(1 for term in keywords if term and term.lower() in text)
        score += sum(5 for term in keywords if term and term.lower() in name)
        if "tests" in symbol.path.parts:
            score -= 3
        if symbol.kind != "function":
            score -= 1
        if score > 0:
            scored.append((score, symbol))
    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], "tests" in item[1].path.parts, str(item[1].path), item[1].line))
    return scored[0][1].path.relative_to(tools.repo_path).as_posix()


def evaluate_retrieval(tasks: list[BenchmarkTask]) -> list[RetrievalResult]:
    model = LocalHeuristicModel()
    results: list[RetrievalResult] = []
    for task in tasks:
        tools = RepoTools(task.repo)
        keywords = model.analyze_issue(task.issue).keywords
        for strategy, selected in (
            ("keyword-file", keyword_top1(task, tools, keywords)),
            ("ast-symbol", ast_symbol_top1(task, tools, keywords)),
        ):
            results.append(
                RetrievalResult(
                    task=task.name,
                    strategy=strategy,
                    selected_file=selected,
                    expected_file=task.expected_file,
                    hit=selected == task.expected_file,
                )
            )
    return results


def summarize_results(results: list[RetrievalResult]) -> dict[str, dict[str, float | int]]:
    summary: dict[str, dict[str, float | int]] = {}
    for strategy in sorted({item.strategy for item in results}):
        strategy_results = [item for item in results if item.strategy == strategy]
        hits = sum(item.hit for item in strategy_results)
        total = len(strategy_results)
        summary[strategy] = {
            "hits": hits,
            "total": total,
            "top1_accuracy": hits / total if total else 0.0,
        }
    return summary


def write_json_report(root: Path, results: list[RetrievalResult]) -> Path:
    output_dir = root / "runs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"ablation-{timestamp}.json"
    payload = {
        "created_at_utc": timestamp,
        "results": [asdict(item) for item in results],
        "summary": summarize_results(results),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def latest_ablation_path(root: Path) -> Path | None:
    reports = sorted((root / "runs").glob("ablation-*.json"))
    return reports[-1] if reports else None


def load_ablation(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def format_results(results: list[RetrievalResult]) -> str:
    lines = ["strategy | task | selected | expected | hit", "--- | --- | --- | --- | ---"]
    for item in results:
        lines.append(
            f"{item.strategy} | {item.task} | {item.selected_file} | {item.expected_file} | {item.hit}"
        )
    lines.append("")
    for strategy, values in summarize_results(results).items():
        lines.append(f"{strategy}={values['hits']}/{values['total']} top-1 localization hits")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare retrieval/localization strategies")
    parser.add_argument("--no-json", action="store_true", help="do not write a timestamped JSON report")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    results = evaluate_retrieval(default_tasks(root))
    print(format_results(results))
    if not args.no_json:
        print(f"json_report={write_json_report(root, results)}")


if __name__ == "__main__":
    main()
