from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def latest_report_path(root: Path) -> Path:
    reports = sorted((root / "runs").glob("benchmark-*.json"))
    if not reports:
        raise FileNotFoundError("No benchmark reports found under runs/. Run `python3 -m autopr_agent.benchmark` first.")
    return reports[-1]


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_summary(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    metrics = report.get("metrics", [])
    lines = ["# AutoPR-Agent Benchmark Report", ""]
    if created_at := report.get("created_at_utc"):
        lines.append(f"created_at_utc={created_at}")
        lines.append("")

    lines.append("## Summary")
    for system, values in summary.items():
        solved = values.get("solved", 0)
        total = values.get("total", 0)
        success_rate = values.get("success_rate", 0.0)
        localized = values.get("localized", 0)
        localization_rate = values.get("localization_rate", 0.0)
        lines.append(
            f"- {system}: {solved}/{total} solved ({success_rate:.0%}), "
            f"localized {localized}/{total} ({localization_rate:.0%})"
        )

    lines.extend(["", "## Tasks", "system | task | success | localized | changed lines | regression failed before | tests passed after"])
    lines.append("--- | --- | --- | --- | --- | --- | ---")
    for item in metrics:
        changed_lines = item.get("patch_changed_lines", 0)
        localized = item.get("localized_expected_file", False)
        lines.append(
            f"{item['system']} | {item['task']} | {item['success']} | {localized} | "
            f"{changed_lines} | {item['regression_failed_before_patch']} | "
            f"{item['tests_passed_after_patch']}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize AutoPR-Agent benchmark JSON reports")
    parser.add_argument("report", nargs="?", type=Path, help="path to a benchmark JSON report")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report_path = args.report or latest_report_path(root)
    print(format_summary(load_report(report_path)))


if __name__ == "__main__":
    main()
