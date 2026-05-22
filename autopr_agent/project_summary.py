from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from autopr_agent.ablation import latest_ablation_path, load_ablation
from autopr_agent.report import latest_report_path, load_report


def _system_line(summary: dict[str, Any], system: str) -> str:
    values = summary.get(system, {})
    total = values.get("total", 0)
    return (
        f"{system}: {values.get('solved', 0)}/{total} solved, "
        f"{values.get('localized', 0)}/{total} localized"
    )


def render_project_summary(root: Path) -> str:
    benchmark = load_report(latest_report_path(root))
    ablation_path = latest_ablation_path(root)
    ablation = load_ablation(ablation_path) if ablation_path else {"summary": {}}
    summary = benchmark.get("summary", {})
    ablation_summary = ablation.get("summary", {})

    ast = ablation_summary.get("ast-symbol", {})
    keyword = ablation_summary.get("keyword-file", {})

    single = summary.get("single-agent", {})
    auto = summary.get("autopr-agent", {})
    single_solved = single.get("solved", 0)
    single_total = single.get("total", 0)
    auto_solved = auto.get("solved", 0)
    auto_total = auto.get("total", 0)
    keyword_hits = keyword.get("hits", 0)
    keyword_total = keyword.get("total", 0)
    ast_hits = ast.get("hits", 0)
    ast_total = ast.get("total", 0)

    lines = [
        "# AutoPR-Agent Project Summary",
        "",
        "## Background",
        "Software maintenance requires more than generating code from a prompt. A bug fix usually involves interpreting the issue, locating relevant code, writing a regression test, applying a minimal patch, running verification, and preparing reviewer-facing evidence.",
        "",
        "## Motivation",
        "Single-agent coding assistants often mix retrieval, reasoning, patching, and verification in one loop. In the seeded benchmark suite, the single-agent baseline repeatedly selects test files instead of source files, causing patch attempts to fail before validation.",
        "",
        "## Goal",
        "AutoPR-Agent aims to turn a bug report into a validated pull-request candidate using specialized agents for issue understanding, code search, AST-based localization, regression-test generation, patching, review, verification, and reporting.",
        "",
        "## Techniques",
        "- Multi-agent workflow orchestration",
        "- Provider-based LLM abstraction with local and OpenAI-compatible backends",
        "- AST symbol indexing and symbol-ranking localization",
        "- Test-first repair loop with before/after verification",
        "- Patch diff tracking and changed-line metrics",
        "- Benchmark, ablation, dashboard, and run-history artifacts",
        "",
        "## Latest Results",
        f"- {_system_line(summary, 'single-agent')}",
        f"- {_system_line(summary, 'autopr-agent')}",
        f"- ast-symbol retrieval: {ast.get('hits', 0)}/{ast.get('total', 0)} top-1 localization hits",
        f"- keyword-file retrieval: {keyword.get('hits', 0)}/{keyword.get('total', 0)} top-1 localization hits",
        "",
        "## CV Bullet",
        f"Built AutoPR-Agent, a multi-agent code repair system that converts bug reports into validated PR candidates using AST-based code localization, regression-test generation, patch synthesis, review, and before/after test verification; on a seeded Python benchmark suite, improved validated repair success from {single_solved}/{single_total} for a single-agent baseline to {auto_solved}/{auto_total} and improved top-1 localization from {keyword_hits}/{keyword_total} keyword retrieval to {ast_hits}/{ast_total} AST-symbol ranking.",
    ]
    return "\n".join(lines) + "\n"


def write_project_summary(root: Path) -> Path:
    output_path = root / "docs" / "PROJECT_SUMMARY.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(render_project_summary(root), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AutoPR-Agent project summary markdown")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(write_project_summary(root))


if __name__ == "__main__":
    main()
