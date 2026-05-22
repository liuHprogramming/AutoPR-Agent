from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from autopr_agent.ablation import latest_ablation_path, load_ablation
from autopr_agent.fixture_guard import fixture_integrity_errors
from autopr_agent.report import latest_report_path, load_report


def _format_system(summary: dict[str, Any], name: str) -> str:
    values = summary.get(name, {})
    total = values.get("total", 0)
    return (
        f"{values.get('solved', 0)}/{total} solved, "
        f"{values.get('localized', 0)}/{total} localized"
    )


def format_status(root: Path) -> str:
    lines = ["# AutoPR-Agent Status", ""]
    fixture_errors = fixture_integrity_errors(root)
    lines.append(f"fixtures={'ok' if not fixture_errors else 'failed'}")
    for error in fixture_errors:
        lines.append(f"- {error}")

    try:
        benchmark_path = latest_report_path(root)
        benchmark = load_report(benchmark_path)
        lines.append(f"latest_benchmark={benchmark_path.name}")
        lines.append(f"single-agent={_format_system(benchmark.get('summary', {}), 'single-agent')}")
        lines.append(f"autopr-agent={_format_system(benchmark.get('summary', {}), 'autopr-agent')}")
    except FileNotFoundError:
        lines.append("latest_benchmark=missing")

    ablation_path = latest_ablation_path(root)
    if ablation_path:
        ablation = load_ablation(ablation_path)
        lines.append(f"latest_ablation={ablation_path.name}")
        for strategy, values in ablation.get("summary", {}).items():
            lines.append(
                f"{strategy}={values.get('hits', 0)}/{values.get('total', 0)} top-1 hits"
            )
    else:
        lines.append("latest_ablation=missing")

    dashboard = root / "runs" / "dashboard.html"
    lines.append(f"dashboard={'present' if dashboard.exists() else 'missing'}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Show AutoPR-Agent demo readiness status")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(format_status(root))


if __name__ == "__main__":
    main()
