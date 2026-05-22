from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

from autopr_agent.ablation import latest_ablation_path, load_ablation
from autopr_agent.report import latest_report_path, load_report


def _system_card(system: str, values: dict[str, Any]) -> str:
    solved = values.get("solved", 0)
    total = values.get("total", 0)
    success_rate = values.get("success_rate", 0.0)
    localized = values.get("localized", 0)
    localization_rate = values.get("localization_rate", 0.0)
    return f"""
    <section class="card">
      <h2>{html.escape(system)}</h2>
      <p class="metric">{solved}/{total}</p>
      <p>solved ({success_rate:.0%})</p>
      <p>{localized}/{total} localized ({localization_rate:.0%})</p>
    </section>
    """


def _task_rows(metrics: list[dict[str, Any]]) -> str:
    rows = []
    for item in metrics:
        status = "pass" if item.get("success") else "fail"
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.get('system', ''))}</td>"
            f"<td>{html.escape(item.get('task', ''))}</td>"
            f"<td class='{status}'>{item.get('success')}</td>"
            f"<td>{item.get('localized_expected_file')}</td>"
            f"<td>{item.get('patch_changed_lines', 0)}</td>"
            f"<td>{item.get('regression_failed_before_patch')}</td>"
            f"<td>{item.get('tests_passed_after_patch')}</td>"
            "</tr>"
        )
    return "".join(rows)


def _detail_sections(details: list[dict[str, Any]]) -> str:
    sections = []
    for item in details:
        events = "".join(f"<li>{html.escape(event)}</li>" for event in item.get("events", []))
        diff = html.escape(item.get("patch_diff", "") or "No patch diff recorded.")
        sections.append(
            f"""
            <section class="detail">
              <h3>{html.escape(item.get('system', ''))} / {html.escape(item.get('task', ''))}</h3>
              <p><strong>Expected:</strong> {html.escape(str(item.get('expected_file')))}</p>
              <p><strong>Selected:</strong> {html.escape(str(item.get('selected_file')))}::{html.escape(str(item.get('selected_symbol')))}</p>
              <p><strong>Review risk:</strong> {html.escape(str(item.get('review_risk_level')))}</p>
              <ol>{events}</ol>
              <pre>{diff}</pre>
            </section>
            """
        )
    return "".join(sections)


def _ablation_section(ablation: dict[str, Any] | None) -> str:
    if not ablation:
        return ""
    rows = []
    for item in ablation.get("results", []):
        status = "pass" if item.get("hit") else "fail"
        rows.append(
            "<tr>"
            f"<td>{html.escape(item.get('strategy', ''))}</td>"
            f"<td>{html.escape(item.get('task', ''))}</td>"
            f"<td>{html.escape(str(item.get('selected_file')))}</td>"
            f"<td>{html.escape(str(item.get('expected_file')))}</td>"
            f"<td class='{status}'>{item.get('hit')}</td>"
            "</tr>"
        )
    summary = []
    for strategy, values in ablation.get("summary", {}).items():
        summary.append(
            f"<p><strong>{html.escape(strategy)}</strong>: "
            f"{values.get('hits', 0)}/{values.get('total', 0)} top-1 hits "
            f"({values.get('top1_accuracy', 0.0):.0%})</p>"
        )
    return f"""
    <h2>Retrieval Ablation</h2>
    <section class="detail">{''.join(summary)}</section>
    <table>
      <thead><tr><th>Strategy</th><th>Task</th><th>Selected</th><th>Expected</th><th>Hit</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def render_dashboard(report: dict[str, Any], ablation: dict[str, Any] | None = None) -> str:
    summary = report.get("summary", {})
    metrics = report.get("metrics", [])
    details = report.get("details", [])
    cards = "".join(_system_card(system, values) for system, values in summary.items())
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoPR-Agent Benchmark Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; margin: 0; background: #f7f8fa; color: #1f2933; }}
    header {{ background: #111827; color: white; padding: 28px 36px; }}
    main {{ padding: 28px 36px; max-width: 1180px; margin: 0 auto; }}
    h1, h2, h3 {{ margin-top: 0; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }}
    .card, .detail, table {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; }}
    .card {{ padding: 20px; }}
    .metric {{ font-size: 42px; font-weight: 700; margin: 0; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; margin-bottom: 28px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; }}
    th {{ background: #eef2f7; }}
    .pass {{ color: #047857; font-weight: 700; }}
    .fail {{ color: #b91c1c; font-weight: 700; }}
    .detail {{ padding: 18px; margin-bottom: 18px; }}
    pre {{ overflow-x: auto; background: #0f172a; color: #e5e7eb; padding: 14px; border-radius: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>AutoPR-Agent Benchmark Dashboard</h1>
    <p>Report: {html.escape(str(report.get('created_at_utc', 'unknown')))}</p>
  </header>
  <main>
    <section class="cards">{cards}</section>
    <h2>Task Results</h2>
    <table>
      <thead><tr><th>System</th><th>Task</th><th>Success</th><th>Localized</th><th>Changed Lines</th><th>Regression Failed Before</th><th>Tests Passed After</th></tr></thead>
      <tbody>{_task_rows(metrics)}</tbody>
    </table>
    <h2>Run Details</h2>
    {_ablation_section(ablation)}
    {_detail_sections(details)}
  </main>
</body>
</html>"""


def write_dashboard(root: Path, report_path: Path | None = None) -> Path:
    report_path = report_path or latest_report_path(root)
    report = load_report(report_path)
    ablation_path = latest_ablation_path(root)
    ablation = load_ablation(ablation_path) if ablation_path else None
    output_path = root / "runs" / "dashboard.html"
    output_path.write_text(render_dashboard(report, ablation), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static HTML dashboard from a benchmark report")
    parser.add_argument("report", nargs="?", type=Path, help="path to a benchmark JSON report")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(write_dashboard(root, args.report))


if __name__ == "__main__":
    main()
