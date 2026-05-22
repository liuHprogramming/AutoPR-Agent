from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_history(root: Path) -> list[dict[str, Any]]:
    index_path = root / "runs" / "index.json"
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        return payload.get("runs", [])

    runs = []
    for report_path in sorted((root / "runs").glob("benchmark-*.json")):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        runs.append(
            {
                "created_at_utc": report.get("created_at_utc", report_path.stem),
                "report": report_path.name,
                "summary": report.get("summary", {}),
            }
        )
    return runs


def format_history(runs: list[dict[str, Any]]) -> str:
    lines = ["# AutoPR-Agent Benchmark History", ""]
    if not runs:
        lines.append("No benchmark runs found.")
        return "\n".join(lines)

    lines.append("created_at_utc | report | single-agent | autopr-agent")
    lines.append("--- | --- | --- | ---")
    for run in runs:
        summary = run.get("summary", {})
        single = summary.get("single-agent", {})
        auto = summary.get("autopr-agent", {})
        single_total = single.get("total", 0)
        auto_total = auto.get("total", 0)
        single_text = (
            f"{single.get('solved', 0)}/{single_total} solved, "
            f"{single.get('localized', 0)}/{single_total} localized"
        )
        auto_text = (
            f"{auto.get('solved', 0)}/{auto_total} solved, "
            f"{auto.get('localized', 0)}/{auto_total} localized"
        )
        lines.append(
            f"{run.get('created_at_utc', '')} | {run.get('report', '')} | "
            f"{single_text} | {auto_text}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="List AutoPR-Agent benchmark run history")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(format_history(load_history(root)))


if __name__ == "__main__":
    main()
