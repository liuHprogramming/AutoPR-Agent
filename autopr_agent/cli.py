from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from autopr_agent.judge import HeuristicPatchJudge, OpenAICompatibleJudge, PatchJudge
from autopr_agent.pr_description import write_pr_description
from autopr_agent.providers.factory import create_provider
from autopr_agent.models import RunState
from autopr_agent.workflow import AutoPRWorkflow


DEMO_TASKS = {
    "math": {
        "repo": Path("benchmarks/seeded_math_bug/repo"),
        "issue": "factorial(0) returns 0, but mathematically it should return 1",
    },
    "text": {
        "repo": Path("benchmarks/seeded_text_bug/repo"),
        "issue": "normalize_whitespace should collapse repeated internal spaces into one space",
    },
    "list": {
        "repo": Path("benchmarks/seeded_list_bug/repo"),
        "issue": "unique_preserve_order should remove duplicates while preserving first-seen order",
    },
}


def add_provider_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=["local", "openai-compatible"],
        default="local",
        help="model provider backend",
    )
    parser.add_argument("--model", help="provider model name")
    parser.add_argument("--base-url", help="OpenAI-compatible chat completions URL")
    parser.add_argument(
        "--api-key-env",
        default="OPENAI_API_KEY",
        help="environment variable containing the API key",
    )


def add_judge_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--judge",
        choices=["heuristic", "openai-compatible"],
        default="heuristic",
        help="patch review judge backend",
    )
    parser.add_argument("--judge-model", help="model name for the OpenAI-compatible judge")
    parser.add_argument("--judge-base-url", help="OpenAI-compatible judge chat completions URL")
    parser.add_argument(
        "--judge-api-key-env",
        default="OPENAI_API_KEY",
        help="environment variable containing the judge API key",
    )


def add_report_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--report-out",
        type=Path,
        help="write the full Markdown run report to this path",
    )
    parser.add_argument(
        "--pr-out",
        type=Path,
        help="write a concise PR description Markdown artifact to this path",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AutoPR-Agent on a local repository")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run the multi-agent repair workflow")
    run_parser.add_argument("repo", type=Path)
    run_parser.add_argument("--issue", required=True)
    add_provider_options(run_parser)
    add_judge_options(run_parser)
    run_parser.add_argument(
        "--workdir-copy",
        action="store_true",
        help="copy repo to a temporary directory before patching",
    )
    add_report_option(run_parser)

    demo_parser = subparsers.add_parser("demo", help="run a seeded demo on a temporary repo copy")
    demo_parser.add_argument("task", choices=sorted(DEMO_TASKS), nargs="?", default="math")
    add_provider_options(demo_parser)
    add_judge_options(demo_parser)
    add_report_option(demo_parser)
    return parser


def create_judge(
    judge_name: str,
    judge_model: str | None,
    judge_base_url: str | None,
    judge_api_key_env: str,
) -> PatchJudge:
    if judge_name == "heuristic":
        return HeuristicPatchJudge()
    if judge_name == "openai-compatible":
        if not judge_model:
            raise ValueError("--judge-model is required for --judge openai-compatible")
        kwargs = {"model": judge_model, "api_key_env": judge_api_key_env}
        if judge_base_url:
            kwargs["base_url"] = judge_base_url
        return OpenAICompatibleJudge(**kwargs)
    raise ValueError(f"Unknown judge: {judge_name}")


def write_report(path: Path, report: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report + "\n", encoding="utf-8")
    return path


def run_workflow(
    repo: Path,
    issue: str,
    provider_name: str,
    model: str | None,
    base_url: str | None,
    api_key_env: str,
    judge_name: str,
    judge_model: str | None,
    judge_base_url: str | None,
    judge_api_key_env: str,
) -> tuple[RunState, str]:
    provider = create_provider(provider_name, model, base_url, api_key_env)
    judge = create_judge(judge_name, judge_model, judge_base_url, judge_api_key_env)
    workflow = AutoPRWorkflow(repo, model=provider, judge=judge)
    state, report = workflow.run(issue)
    return state, report


def run_on_copy(
    repo: Path,
    issue: str,
    provider_name: str,
    model: str | None,
    base_url: str | None,
    api_key_env: str,
    judge_name: str,
    judge_model: str | None,
    judge_base_url: str | None,
    judge_api_key_env: str,
) -> tuple[RunState, str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        copied_repo = Path(tmpdir) / repo.name
        shutil.copytree(repo, copied_repo)
        print(f"Using temporary repo copy: {copied_repo}")
        return run_workflow(copied_repo, issue, provider_name, model, base_url, api_key_env, judge_name, judge_model, judge_base_url, judge_api_key_env)


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "run":
        if args.workdir_copy:
            state, report = run_on_copy(
                args.repo,
                args.issue,
                args.provider,
                args.model,
                args.base_url,
                args.api_key_env,
                args.judge,
                args.judge_model,
                args.judge_base_url,
                args.judge_api_key_env,
            )
        else:
            state, report = run_workflow(
                args.repo,
                args.issue,
                args.provider,
                args.model,
                args.base_url,
                args.api_key_env,
                args.judge,
                args.judge_model,
                args.judge_base_url,
                args.judge_api_key_env,
            )
        if args.report_out:
            print(f"Report written: {write_report(args.report_out, report)}")
        if args.pr_out:
            print(f"PR description written: {write_pr_description(args.pr_out, state)}")
        print(report)
        return

    if args.command == "demo":
        root = Path(__file__).resolve().parents[1]
        task = DEMO_TASKS[args.task]
        repo = root / task["repo"]
        print(f"Demo task: {args.task}")
        print(f"Issue: {task['issue']}")
        state, report = run_on_copy(
            repo,
            task["issue"],
            args.provider,
            args.model,
            args.base_url,
            args.api_key_env,
            args.judge,
            args.judge_model,
            args.judge_base_url,
            args.judge_api_key_env,
        )
        if args.report_out:
            print(f"Report written: {write_report(args.report_out, report)}")
        if args.pr_out:
            print(f"PR description written: {write_pr_description(args.pr_out, state)}")
        print(report)


if __name__ == "__main__":
    main()
