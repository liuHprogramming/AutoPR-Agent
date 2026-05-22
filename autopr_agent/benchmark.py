from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from autopr_agent.baselines import SingleAgentBaseline
from autopr_agent.workflow import AutoPRWorkflow


@dataclass(frozen=True)
class BenchmarkTask:
    name: str
    repo: Path
    issue: str
    expected_file: str


def default_tasks(root: Path) -> list[BenchmarkTask]:
    return [
        BenchmarkTask(
            name="seeded_math_bug",
            repo=root / "benchmarks" / "seeded_math_bug" / "repo",
            issue="factorial(0) returns 0, but mathematically it should return 1",
            expected_file="src/math_utils.py",
        ),
        BenchmarkTask(
            name="seeded_text_bug",
            repo=root / "benchmarks" / "seeded_text_bug" / "repo",
            issue="normalize_whitespace should collapse repeated internal spaces into one space",
            expected_file="src/text_utils.py",
        ),
        BenchmarkTask(
            name="seeded_list_bug",
            repo=root / "benchmarks" / "seeded_list_bug" / "repo",
            issue="unique_preserve_order should remove duplicates while preserving first-seen order",
            expected_file="src/list_utils.py",
        ),
        BenchmarkTask(
            name="seeded_dict_bug",
            repo=root / "benchmarks" / "seeded_dict_bug" / "repo",
            issue="merge_defaults should preserve default keys unless overrides replace them",
            expected_file="src/dict_utils.py",
        ),
    ]


@dataclass(frozen=True)
class RunMetrics:
    system: str
    task: str
    success: bool
    regression_failed_before_patch: bool
    tests_passed_after_patch: bool
    patch_applied: bool
    localized_expected_file: bool
    suspicious_symbol_count: int
    patch_changed_lines: int
    event_count: int


@dataclass(frozen=True)
class RunDetail:
    system: str
    task: str
    issue: str
    expected_file: str
    selected_file: str | None
    selected_symbol: str | None
    events: list[str]
    patch_diff: str
    review_approved: bool | None
    review_issues: list[str]
    review_checklist: dict[str, bool]
    review_risk_level: str | None


def selected_symbol_info(state) -> tuple[str | None, str | None]:
    if not state.suspicious_symbols:
        return None, None
    symbol = state.suspicious_symbols[0]
    return symbol.path.relative_to(state.repo_path).as_posix(), symbol.name


def build_detail(system: str, task: BenchmarkTask, state) -> RunDetail:
    selected_file, selected_symbol = selected_symbol_info(state)
    return RunDetail(
        system=system,
        task=task.name,
        issue=task.issue,
        expected_file=task.expected_file,
        selected_file=selected_file,
        selected_symbol=selected_symbol,
        events=list(state.events),
        patch_diff=state.patch_diff,
        review_approved=state.review.approved if state.review else None,
        review_issues=list(state.review.issues) if state.review else [],
        review_checklist=dict(state.review.checklist) if state.review else {},
        review_risk_level=state.review.risk_level if state.review else None,
    )


def evaluate_state(system: str, task: BenchmarkTask, state) -> RunMetrics:
    before_valid = state.verification_before is not None and not state.verification_before.passed
    after_valid = state.verification_after is not None and state.verification_after.passed
    selected_file, _ = selected_symbol_info(state)
    localized_expected_file = selected_file == task.expected_file
    success = after_valid and state.patch_applied
    if system == "autopr-agent":
        success = success and before_valid and bool(state.review and state.review.approved)
    return RunMetrics(
        system=system,
        task=task.name,
        success=success,
        regression_failed_before_patch=before_valid,
        tests_passed_after_patch=after_valid,
        patch_applied=state.patch_applied,
        localized_expected_file=localized_expected_file,
        suspicious_symbol_count=len(state.suspicious_symbols),
        patch_changed_lines=state.patch_changed_lines,
        event_count=len(state.events),
    )


def run_system(task: BenchmarkTask, system: str, verbose: bool = True) -> tuple[RunMetrics, RunDetail]:
    with tempfile.TemporaryDirectory() as tmpdir:
        work_repo = Path(tmpdir) / f"{task.name}-{system}"
        shutil.copytree(task.repo, work_repo)
        runner = AutoPRWorkflow(work_repo) if system == "autopr-agent" else SingleAgentBaseline(work_repo)
        state, report = runner.run(task.issue)
        metrics = evaluate_state(system, task, state)
        detail = build_detail(system, task, state)
        if verbose:
            print(report)
            print()
            print(f"system={metrics.system}")
            print(f"benchmark_task={task.name}")
            print(f"regression_failed_before_patch={metrics.regression_failed_before_patch}")
            print(f"tests_passed_after_patch={metrics.tests_passed_after_patch}")
            print(f"patch_applied={metrics.patch_applied}")
            print(f"localized_expected_file={metrics.localized_expected_file}")
            print(f"patch_changed_lines={metrics.patch_changed_lines}")
            print(f"success={metrics.success}")
            print()
        return metrics, detail


def summarize(metrics: list[RunMetrics], systems: list[str]) -> dict[str, dict[str, float | int]]:
    summary: dict[str, dict[str, float | int]] = {}
    for system in systems:
        system_metrics = [item for item in metrics if item.system == system]
        successes = sum(item.success for item in system_metrics)
        localized = sum(item.localized_expected_file for item in system_metrics)
        total = len(system_metrics)
        summary[system] = {
            "solved": successes,
            "total": total,
            "success_rate": successes / total if total else 0.0,
            "localized": localized,
            "localization_rate": localized / total if total else 0.0,
        }
    return summary


def append_run_index(output_dir: Path, report_path: Path, timestamp: str, summary: dict[str, dict[str, float | int]]) -> None:
    index_path = output_dir / "index.json"
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        payload = {"runs": []}
    payload["runs"].append(
        {
            "created_at_utc": timestamp,
            "report": report_path.name,
            "summary": summary,
        }
    )
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_json_report(
    root: Path,
    metrics: list[RunMetrics],
    details: list[RunDetail],
    summary: dict[str, dict[str, float | int]],
) -> Path:
    output_dir = root / "runs"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"benchmark-{timestamp}.json"
    payload = {
        "created_at_utc": timestamp,
        "metrics": [asdict(item) for item in metrics],
        "details": [asdict(item) for item in details],
        "summary": summary,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    append_run_index(output_dir, output_path, timestamp, summary)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AutoPR-Agent benchmark tasks")
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="do not write a timestamped JSON report under runs/",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = default_tasks(root)
    systems = ["single-agent", "autopr-agent"]
    results = [run_system(task, system) for task in tasks for system in systems]
    metrics = [item[0] for item in results]
    details = [item[1] for item in results]
    summary = summarize(metrics, systems)

    print()
    print("## Benchmark Summary")
    for system in systems:
        system_summary = summary[system]
        print(f"{system}={system_summary['solved']}/{system_summary['total']} tasks solved")
    if not args.no_json:
        output_path = write_json_report(root, metrics, details, summary)
        print(f"json_report={output_path}")


if __name__ == "__main__":
    main()
