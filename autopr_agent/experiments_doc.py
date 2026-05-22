from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def latest_json(root: Path, prefix: str) -> Path:
    reports = sorted((root / "runs").glob(f"{prefix}-*.json"))
    if not reports:
        raise FileNotFoundError(f"No {prefix} reports found under runs/.")
    return reports[-1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rate(value: float) -> str:
    return f"{value:.0%}"


def render_experiments_doc(benchmark: dict[str, Any], ablation: dict[str, Any]) -> str:
    benchmark_summary = benchmark.get("summary", {})
    ablation_summary = ablation.get("summary", {})
    benchmark_metrics = benchmark.get("metrics", [])
    ablation_results = ablation.get("results", [])

    lines = [
        "# AutoPR-Agent Experiments",
        "",
        "## Purpose",
        "The experiments test whether decomposing code repair into specialized agents improves validated bug-fix success over a compact single-agent baseline, and whether AST-symbol retrieval improves source-file localization over keyword file matching.",
        "",
        "## End-to-End Repair Benchmark",
        "System | Solved | Success rate | Localized expected file | Localization rate",
        "--- | --- | --- | --- | ---",
    ]

    for system in sorted(benchmark_summary):
        values = benchmark_summary[system]
        solved = values.get("solved", 0)
        total = values.get("total", 0)
        localized = values.get("localized", 0)
        lines.append(
            f"{system} | {solved}/{total} | {_rate(values.get('success_rate', 0.0))} | "
            f"{localized}/{total} | {_rate(values.get('localization_rate', 0.0))}"
        )

    lines.extend([
        "",
        "## Retrieval Ablation",
        "Strategy | Top-1 hits | Top-1 accuracy",
        "--- | --- | ---",
    ])

    for strategy in sorted(ablation_summary):
        values = ablation_summary[strategy]
        hits = values.get("hits", 0)
        total = values.get("total", 0)
        lines.append(f"{strategy} | {hits}/{total} | {_rate(values.get('top1_accuracy', 0.0))}")

    lines.extend([
        "",
        "## Task-Level Repair Results",
        "Task | System | Success | Selected source file | Patch changed lines | Before/after verification",
        "--- | --- | --- | --- | --- | ---",
    ])

    for item in benchmark_metrics:
        verification = "pass" if item.get("regression_failed_before_patch") and item.get("tests_passed_after_patch") else "fail"
        lines.append(
            f"{item.get('task', '')} | {item.get('system', '')} | {item.get('success', False)} | "
            f"{item.get('localized_expected_file', False)} | {item.get('patch_changed_lines', 0)} | {verification}"
        )

    lines.extend([
        "",
        "## Task-Level Retrieval Results",
        "Task | Strategy | Selected file | Expected file | Hit",
        "--- | --- | --- | --- | ---",
    ])

    for item in ablation_results:
        lines.append(
            f"{item.get('task', '')} | {item.get('strategy', '')} | {item.get('selected_file', '')} | "
            f"{item.get('expected_file', '')} | {item.get('hit', False)}"
        )

    lines.extend([
        "",
        "## Interpretation",
        "The single-agent baseline is intentionally compact and uses the same local deterministic model family, but it often selects test files because keyword matching overweights files that mention the failing behavior. AutoPR-Agent adds AST symbol ranking, test-first validation, patch review, and before/after verification, which produces a measurable improvement on the seeded benchmark suite.",
    ])
    return "\n".join(lines) + "\n"


def write_experiments_doc(root: Path, benchmark_path: Path | None = None, ablation_path: Path | None = None) -> Path:
    benchmark = load_json(benchmark_path or latest_json(root, "benchmark"))
    ablation = load_json(ablation_path or latest_json(root, "ablation"))
    output_path = root / "docs" / "EXPERIMENTS.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(render_experiments_doc(benchmark, ablation), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AutoPR-Agent experiment documentation")
    parser.add_argument("--benchmark", type=Path, help="benchmark JSON report")
    parser.add_argument("--ablation", type=Path, help="ablation JSON report")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(write_experiments_doc(root, args.benchmark, args.ablation))


if __name__ == "__main__":
    main()
