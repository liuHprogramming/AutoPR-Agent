from __future__ import annotations

import argparse
from pathlib import Path

from autopr_agent.benchmark import BenchmarkTask, default_tasks


TASK_NOTES = {
    "seeded_math_bug": {
        "category": "numeric edge case",
        "bug": "factorial(0) returns 0 instead of 1",
        "expected_fix": "return 1 for the zero case",
        "why": "Tests whether the repair loop can localize a small boundary-condition bug.",
    },
    "seeded_text_bug": {
        "category": "string normalization",
        "bug": "normalize_whitespace strips outer whitespace but keeps repeated internal spaces",
        "expected_fix": "split and rejoin text so repeated whitespace collapses to one space",
        "why": "Tests whether generated regression tests capture behavior beyond the existing tests.",
    },
    "seeded_list_bug": {
        "category": "list ordering",
        "bug": "unique_preserve_order removes duplicates by sorting, which changes first-seen order",
        "expected_fix": "track seen values and append each new item once",
        "why": "Tests whether patching preserves semantic ordering instead of only satisfying uniqueness.",
    },
    "seeded_dict_bug": {
        "category": "dictionary merge semantics",
        "bug": "merge_defaults returns only overrides and drops default-only keys",
        "expected_fix": "copy defaults, then update them with overrides",
        "why": "Tests whether the workflow handles stateful data-structure behavior beyond scalars and strings.",
    },
}


def render_task_row(task: BenchmarkTask) -> str:
    note = TASK_NOTES.get(task.name, {})
    return (
        f"{task.name} | {note.get('category', 'unknown')} | `{task.expected_file}` | "
        f"{note.get('bug', task.issue)} | {note.get('expected_fix', 'see issue')}"
    )


def render_benchmark_catalog(root: Path) -> str:
    tasks = default_tasks(root)
    lines = [
        "# AutoPR-Agent Benchmark Catalog",
        "",
        "The seeded benchmark suite is designed to evaluate whether AutoPR-Agent can move from a natural-language bug report to a validated patch while avoiding the common failure mode of patching or over-weighting test files.",
        "",
        "## Tasks",
        "Task | Category | Expected source file | Seeded bug | Expected repair",
        "--- | --- | --- | --- | ---",
    ]
    lines.extend(render_task_row(task) for task in tasks)
    lines.extend([
        "",
        "## Why These Tasks",
    ])
    for task in tasks:
        note = TASK_NOTES.get(task.name, {})
        lines.append(f"- {task.name}: {note.get('why', 'Covers a seeded repair behavior.')}")
    lines.extend([
        "",
        "## Evaluation Contract",
        "A successful AutoPR-Agent run must localize the expected source file, generate a regression test that fails before the patch, apply a minimal source patch, pass tests after the patch, and pass the review checklist.",
    ])
    return "\n".join(lines) + "\n"


def write_benchmark_catalog(root: Path) -> Path:
    output_path = root / "docs" / "BENCHMARKS.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(render_benchmark_catalog(root), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AutoPR-Agent benchmark catalog")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(write_benchmark_catalog(root))


if __name__ == "__main__":
    main()
