from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from autopr_agent.ablation import evaluate_retrieval, write_json_report as write_ablation_report
from autopr_agent.benchmark import default_tasks, run_system, summarize, write_json_report as write_benchmark_report
from autopr_agent.dashboard import write_dashboard
from autopr_agent.fixture_guard import fixture_integrity_errors
from autopr_agent.report import format_summary, load_report


@dataclass(frozen=True)
class EvaluationArtifacts:
    benchmark_report: Path
    ablation_report: Path
    dashboard: Path


def run_evaluation(root: Path, verbose: bool = False) -> EvaluationArtifacts:
    errors = fixture_integrity_errors(root)
    if errors:
        joined = "\n".join(errors)
        raise RuntimeError(f"Fixture integrity check failed:\n{joined}")

    tasks = default_tasks(root)
    systems = ["single-agent", "autopr-agent"]
    benchmark_results = [run_system(task, system, verbose=verbose) for task in tasks for system in systems]
    metrics = [item[0] for item in benchmark_results]
    details = [item[1] for item in benchmark_results]
    summary = summarize(metrics, systems)
    benchmark_report = write_benchmark_report(root, metrics, details, summary)

    retrieval_results = evaluate_retrieval(tasks)
    ablation_report = write_ablation_report(root, retrieval_results)
    dashboard = write_dashboard(root, benchmark_report)
    return EvaluationArtifacts(
        benchmark_report=benchmark_report,
        ablation_report=ablation_report,
        dashboard=dashboard,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full AutoPR-Agent evaluation pipeline")
    parser.add_argument("--verbose", action="store_true", help="print per-agent benchmark traces")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = run_evaluation(root, verbose=args.verbose)
    print("## Evaluation Complete")
    print(f"benchmark_report={artifacts.benchmark_report}")
    print(f"ablation_report={artifacts.ablation_report}")
    print(f"dashboard={artifacts.dashboard}")
    print()
    print(format_summary(load_report(artifacts.benchmark_report)))


if __name__ == "__main__":
    main()
