from __future__ import annotations

import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path

from autopr_agent.ablation import evaluate_retrieval, format_results, summarize_results
from autopr_agent.architecture_doc import render_architecture_doc
from autopr_agent.agents import BugLocalizationAgent, ReviewAgent
from autopr_agent.baselines import SingleAgentBaseline
from autopr_agent.benchmark import BenchmarkTask, RunMetrics, build_detail, default_tasks, run_system, summarize
from autopr_agent.benchmark_catalog import render_benchmark_catalog
from autopr_agent.cli import DEMO_TASKS, build_parser, write_report
from autopr_agent.dashboard import render_dashboard
from autopr_agent.evaluate import EvaluationArtifacts
from autopr_agent.experiments_doc import render_experiments_doc
from autopr_agent.examples import generate_example_artifacts
from autopr_agent.fixture_guard import fixture_integrity_errors
from autopr_agent.formatting import normalize_diff_paths
from autopr_agent.history import format_history
from autopr_agent.indexer import build_index, format_index
from autopr_agent.judge import HeuristicPatchJudge, OpenAICompatibleJudge, build_judge_payload
from autopr_agent.llm import LocalHeuristicModel, ModelProvider
from autopr_agent.models import IssueAnalysis, PatchPlan, RunState, TestPlan
from autopr_agent.pr_description import render_pr_description, write_pr_description
from autopr_agent.providers.factory import create_provider
from autopr_agent.project_summary import render_project_summary
from autopr_agent.providers.openai_compatible import OpenAICompatibleProvider, ProviderConfigurationError
from autopr_agent.tools import RepoTools
from autopr_agent.report import format_summary
from autopr_agent.status import format_status
from autopr_agent.workflow import AutoPRWorkflow


ROOT = Path(__file__).resolve().parents[1]
MATH_BENCHMARK_REPO = ROOT / "benchmarks" / "seeded_math_bug" / "repo"
TEXT_BENCHMARK_REPO = ROOT / "benchmarks" / "seeded_text_bug" / "repo"
LIST_BENCHMARK_REPO = ROOT / "benchmarks" / "seeded_list_bug" / "repo"
DICT_BENCHMARK_REPO = ROOT / "benchmarks" / "seeded_dict_bug" / "repo"


class TestAutoPRWorkflow(unittest.TestCase):
    def test_evaluation_artifacts_shape(self) -> None:
        artifacts = EvaluationArtifacts(
            benchmark_report=ROOT / "runs" / "benchmark-test.json",
            ablation_report=ROOT / "runs" / "ablation-test.json",
            dashboard=ROOT / "runs" / "dashboard.html",
        )

        self.assertEqual(artifacts.dashboard.name, "dashboard.html")

    def test_seeded_benchmark_fixtures_are_unmodified(self) -> None:
        self.assertEqual(fixture_integrity_errors(ROOT), [])

    def test_seeded_factorial_bug_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)

            workflow = AutoPRWorkflow(repo)
            state, report = workflow.run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )

            self.assertIsNotNone(state.verification_before)
            self.assertIsNotNone(state.verification_after)
            self.assertFalse(state.verification_before.passed)
            self.assertTrue(state.verification_after.passed)
            self.assertIn("Patch candidate validated", report)

    def test_seeded_text_bug_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(TEXT_BENCHMARK_REPO, repo)

            workflow = AutoPRWorkflow(repo)
            state, report = workflow.run(
                "normalize_whitespace should collapse repeated internal spaces into one space"
            )

            self.assertIsNotNone(state.verification_before)
            self.assertIsNotNone(state.verification_after)
            self.assertFalse(state.verification_before.passed)
            self.assertTrue(state.verification_after.passed)
            self.assertIn("Patch candidate validated", report)

    def test_seeded_list_bug_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(LIST_BENCHMARK_REPO, repo)

            workflow = AutoPRWorkflow(repo)
            state, report = workflow.run(
                "unique_preserve_order should remove duplicates while preserving first-seen order"
            )

            self.assertIsNotNone(state.verification_before)
            self.assertIsNotNone(state.verification_after)
            self.assertFalse(state.verification_before.passed)
            self.assertTrue(state.verification_after.passed)
            self.assertIn("Patch candidate validated", report)

    def test_seeded_dict_bug_is_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(DICT_BENCHMARK_REPO, repo)

            workflow = AutoPRWorkflow(repo)
            state, report = workflow.run(
                "merge_defaults should preserve default keys unless overrides replace them"
            )

            self.assertIsNotNone(state.verification_before)
            self.assertIsNotNone(state.verification_after)
            self.assertFalse(state.verification_before.passed)
            self.assertTrue(state.verification_after.passed)
            self.assertEqual(state.suspicious_symbols[0].name, "merge_defaults")
            self.assertIn("Patch candidate validated", report)

    def test_local_model_satisfies_provider_protocol(self) -> None:
        provider: ModelProvider = LocalHeuristicModel()
        analysis = provider.analyze_issue("factorial(0) returns 0")

        self.assertIn("factorial", analysis.keywords)

    def test_cli_parser_accepts_provider_and_workdir_copy(self) -> None:
        args = build_parser().parse_args([
            "run",
            "benchmarks/seeded_math_bug/repo",
            "--issue",
            "factorial(0) returns 0",
            "--provider",
            "local",
            "--workdir-copy",
        ])

        self.assertEqual(args.provider, "local")
        self.assertTrue(args.workdir_copy)

    def test_cli_parser_accepts_seeded_demo_task(self) -> None:
        args = build_parser().parse_args(["demo", "text", "--provider", "local", "--judge", "heuristic"])

        self.assertEqual(args.command, "demo")
        self.assertEqual(args.task, "text")
        self.assertEqual(args.judge, "heuristic")
        self.assertIn("text", DEMO_TASKS)
        self.assertIn("normalize_whitespace", DEMO_TASKS["text"]["issue"])

    def test_cli_parser_accepts_report_output_path(self) -> None:
        args = build_parser().parse_args([
            "demo",
            "math",
            "--report-out",
            "runs/demo-report.md",
            "--pr-out",
            "runs/PR_DESCRIPTION.md",
        ])

        self.assertEqual(args.report_out, Path("runs/demo-report.md"))
        self.assertEqual(args.pr_out, Path("runs/PR_DESCRIPTION.md"))

    def test_write_report_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "report.md"

            written = write_report(output_path, "# Demo Report")

            self.assertEqual(written, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "# Demo Report\n")

    def test_pr_description_renders_pr_body_with_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)
            state, _ = AutoPRWorkflow(repo).run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )

            output = render_pr_description(state)

            self.assertIn("# Fix: factorial(0) returns 0, but mathematically it should return 1", output)
            self.assertIn("Patch target: `src/math_utils.py`", output)
            self.assertIn("Regression test: `tests/test_factorial_regression.py`", output)
            self.assertIn("Tests passed after patch: pass", output)
            self.assertIn("## Diff", output)
            self.assertIn("## LLM-as-Judge", output)
            self.assertIn("Provider: heuristic-judge", output)
            self.assertIn("--- src/math_utils.py", output)
            self.assertNotIn(str(repo), output)

    def test_write_pr_description_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)
            state, _ = AutoPRWorkflow(repo).run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )
            output_path = Path(tmpdir) / "nested" / "PR_DESCRIPTION.md"

            written = write_pr_description(output_path, state)

            self.assertEqual(written, output_path)
            self.assertIn("Patch target: `src/math_utils.py`", output_path.read_text(encoding="utf-8"))

    def test_pyproject_exposes_console_script(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["scripts"]["autopr-agent"], "autopr_agent.cli:main")

    def test_provider_factory_creates_local_provider(self) -> None:
        provider = create_provider("local")
        analysis = provider.analyze_issue("factorial(0) returns 0")

        self.assertIn("factorial", analysis.keywords)

    def test_provider_factory_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ValueError):
            create_provider("missing")

    def test_openai_provider_requires_api_key(self) -> None:
        provider = OpenAICompatibleProvider(model="example-model", api_key_env="AUTOPR_TEST_MISSING_KEY")

        with self.assertRaises(ProviderConfigurationError):
            provider.analyze_issue("factorial(0) returns 0")

    def test_openai_compatible_judge_requires_api_key(self) -> None:
        judge = OpenAICompatibleJudge(model="example-model", api_key_env="AUTOPR_TEST_MISSING_KEY")
        state = RunState(repo_path=MATH_BENCHMARK_REPO, issue_text="factorial(0) returns 0")

        with self.assertRaises(ProviderConfigurationError):
            judge.judge(state, {}, [])

    def test_ast_localizer_prioritizes_source_symbol(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)
            state = RunState(
                repo_path=repo,
                issue_text="factorial(0) returns 0",
                analysis=IssueAnalysis(
                    title="factorial zero bug",
                    expected_behavior="factorial(0) should return 1",
                    observed_behavior="factorial(0) returns 0",
                    keywords=["factorial", "0"],
                ),
            )

            BugLocalizationAgent(RepoTools(repo)).run(state)

            self.assertGreater(len(state.suspicious_symbols), 0)
            self.assertEqual(
                state.suspicious_symbols[0].path.relative_to(repo.resolve()).as_posix(),
                "src/math_utils.py",
            )
            self.assertEqual(state.suspicious_symbols[0].name, "factorial")

    def test_indexer_extracts_python_symbols(self) -> None:
        index = build_index(MATH_BENCHMARK_REPO)
        rendered = format_index(index)

        self.assertIn({
            "name": "factorial",
            "kind": "function",
            "path": "src/math_utils.py",
            "line": 1,
            "end_line": 9,
        }, index)
        self.assertIn("function | factorial | src/math_utils.py | 1", rendered)

    def test_normalize_diff_paths_uses_repo_relative_headers(self) -> None:
        repo = Path("/tmp/example/repo")
        diff = "--- /tmp/example/repo/src/math_utils.py\n+++ /tmp/example/repo/src/math_utils.py\n@@ -1 +1 @@"

        output = normalize_diff_paths(diff, repo)

        self.assertIn("--- src/math_utils.py", output)
        self.assertIn("+++ src/math_utils.py", output)
        self.assertNotIn("/tmp/example/repo", output)

    def test_single_agent_baseline_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)

            state, report = SingleAgentBaseline(repo).run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )

            self.assertIsNotNone(state.verification_after)
            self.assertIn("Single-agent baseline", report)

    def test_review_agent_rejects_test_file_patch(self) -> None:
        state = RunState(
            repo_path=MATH_BENCHMARK_REPO,
            issue_text="bad patch",
            patch_plan=PatchPlan(
                path=MATH_BENCHMARK_REPO / "tests" / "test_math_utils.py",
                original="x",
                replacement="y",
                reason="bad target",
            ),
            patch_applied=True,
            patch_changed_lines=2,
            test_plan=TestPlan(
                path=MATH_BENCHMARK_REPO / "tests" / "test_regression.py",
                content="",
                command=["python3", "-m", "unittest"],
            ),
        )

        ReviewAgent().run(state)

        self.assertIsNotNone(state.review)
        self.assertFalse(state.review.approved)
        self.assertFalse(state.review.checklist["patch_targets_source"])
        self.assertIn("Patch targets a test file instead of source code.", state.review.issues)

    def test_run_detail_records_selected_file_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)

            state, _ = AutoPRWorkflow(repo).run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )
            detail = build_detail("autopr-agent", type("Task", (), {
                "name": "seeded_math_bug",
                "issue": "factorial(0) returns 0, but mathematically it should return 1",
                "expected_file": "src/math_utils.py",
            })(), state)

            self.assertEqual(detail.selected_file, "src/math_utils.py")
            self.assertEqual(detail.selected_symbol, "factorial")
            self.assertTrue(detail.patch_diff.startswith("---"))
            self.assertEqual(detail.review_risk_level, "low")
            self.assertEqual(detail.judge_provider, "heuristic-judge")
            self.assertEqual(detail.judge_score, 100)
            self.assertTrue(detail.judge_approved)
            self.assertGreater(len(detail.events), 0)

    def test_default_benchmark_tasks_include_dict_bug(self) -> None:
        tasks = default_tasks(ROOT)

        self.assertIn("seeded_dict_bug", {task.name for task in tasks})
        self.assertEqual(len(tasks), 4)

    def test_heuristic_patch_judge_scores_validated_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            shutil.copytree(MATH_BENCHMARK_REPO, repo)
            state, _ = AutoPRWorkflow(repo).run(
                "factorial(0) returns 0, but mathematically it should return 1"
            )

            self.assertIsNotNone(state.review)
            self.assertIsNotNone(state.review.judge)
            self.assertEqual(state.review.judge.provider, "heuristic-judge")
            self.assertEqual(state.review.judge.score, 100)
            self.assertIn("patch_diff", build_judge_payload(state, state.review.checklist, state.review.issues))

    def test_benchmark_run_system_supports_quiet_mode(self) -> None:
        task = BenchmarkTask(
            name="seeded_math_bug",
            repo=MATH_BENCHMARK_REPO,
            issue="factorial(0) returns 0, but mathematically it should return 1",
            expected_file="src/math_utils.py",
        )

        metrics, detail = run_system(task, "autopr-agent", verbose=False)

        self.assertTrue(metrics.success)
        self.assertEqual(detail.selected_file, "src/math_utils.py")

    def test_benchmark_summary_calculates_success_rates(self) -> None:
        metrics = [
            RunMetrics("single-agent", "a", False, False, False, False, False, 1, 0, 4),
            RunMetrics("autopr-agent", "a", True, True, True, True, True, 2, 2, 8),
        ]

        summary = summarize(metrics, ["single-agent", "autopr-agent"])

        self.assertEqual(summary["single-agent"]["success_rate"], 0.0)
        self.assertEqual(summary["autopr-agent"]["success_rate"], 1.0)
        self.assertEqual(summary["single-agent"]["localization_rate"], 0.0)
        self.assertEqual(summary["autopr-agent"]["localization_rate"], 1.0)

    def test_retrieval_ablation_compares_keyword_and_ast(self) -> None:
        tasks = [
            BenchmarkTask(
                name="seeded_math_bug",
                repo=MATH_BENCHMARK_REPO,
                issue="factorial(0) returns 0, but mathematically it should return 1",
                expected_file="src/math_utils.py",
            )
        ]

        results = evaluate_retrieval(tasks)
        rendered = format_results(results)

        self.assertEqual(len(results), 2)
        self.assertIn("keyword-file", rendered)
        self.assertIn("ast-symbol", rendered)
        self.assertIn("top-1 localization hits", rendered)
        self.assertEqual(summarize_results(results)["ast-symbol"]["top1_accuracy"], 1.0)

    def test_report_summary_formats_metrics(self) -> None:
        report = {
            "created_at_utc": "20260101T000000Z",
            "summary": {
                "single-agent": {
                    "solved": 0,
                    "total": 1,
                    "success_rate": 0.0,
                    "localized": 0,
                    "localization_rate": 0.0,
                },
                "autopr-agent": {
                    "solved": 1,
                    "total": 1,
                    "success_rate": 1.0,
                    "localized": 1,
                    "localization_rate": 1.0,
                },
            },
            "metrics": [
                {
                    "system": "autopr-agent",
                    "task": "seeded_math_bug",
                    "success": True,
                    "regression_failed_before_patch": True,
                    "tests_passed_after_patch": True,
                    "patch_changed_lines": 2,
                    "localized_expected_file": True,
                }
            ],
        }

        output = format_summary(report)

        self.assertIn("autopr-agent: 1/1 solved (100%), localized 1/1 (100%)", output)
        self.assertIn("autopr-agent | seeded_math_bug | True | True | 2", output)

    def test_history_formats_runs(self) -> None:
        output = format_history(
            [
                {
                    "created_at_utc": "20260101T000000Z",
                    "report": "benchmark-20260101T000000Z.json",
                    "summary": {
                        "single-agent": {"solved": 0, "total": 2, "localized": 0},
                        "autopr-agent": {"solved": 2, "total": 2, "localized": 2},
                    },
                }
            ]
        )

        self.assertIn("benchmark-20260101T000000Z.json", output)
        self.assertIn("2/2 solved, 2/2 localized", output)

    def test_architecture_doc_contains_mermaid_diagrams(self) -> None:
        output = render_architecture_doc()

        self.assertIn("```mermaid", output)
        self.assertIn("IssueUnderstandingAgent", output)
        self.assertIn("Evaluation Flow", output)

    def test_project_summary_renders_cv_bullet(self) -> None:
        output = render_project_summary(ROOT)

        self.assertIn("AutoPR-Agent Project Summary", output)
        self.assertIn("CV Bullet", output)
        self.assertIn("autopr-agent", output)

    def test_benchmark_catalog_lists_seeded_tasks(self) -> None:
        output = render_benchmark_catalog(ROOT)

        self.assertIn("AutoPR-Agent Benchmark Catalog", output)
        self.assertIn("seeded_math_bug", output)
        self.assertIn("seeded_dict_bug", output)
        self.assertIn("dictionary merge semantics", output)
        self.assertIn("Evaluation Contract", output)

    def test_generate_example_artifacts_writes_stable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "project"
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("__pycache__", "runs"))

            written = generate_example_artifacts(root)

            names = {path.name for path in written}
            self.assertEqual(names, {"README.md", "PR_DESCRIPTION.md", "RUN_REPORT.md"})
            self.assertIn("src/math_utils.py", (root / "examples" / "PR_DESCRIPTION.md").read_text(encoding="utf-8"))
            self.assertNotIn("/private/var", (root / "examples" / "PR_DESCRIPTION.md").read_text(encoding="utf-8"))

    def test_experiments_doc_renders_benchmark_and_ablation_tables(self) -> None:
        output = render_experiments_doc(
            {
                "summary": {
                    "single-agent": {
                        "solved": 0,
                        "total": 1,
                        "success_rate": 0.0,
                        "localized": 0,
                        "localization_rate": 0.0,
                    },
                    "autopr-agent": {
                        "solved": 1,
                        "total": 1,
                        "success_rate": 1.0,
                        "localized": 1,
                        "localization_rate": 1.0,
                    },
                },
                "metrics": [
                    {
                        "task": "seeded_math_bug",
                        "system": "autopr-agent",
                        "success": True,
                        "localized_expected_file": True,
                        "patch_changed_lines": 2,
                        "regression_failed_before_patch": True,
                        "tests_passed_after_patch": True,
                    }
                ],
            },
            {
                "summary": {
                    "keyword-file": {"hits": 0, "total": 1, "top1_accuracy": 0.0},
                    "ast-symbol": {"hits": 1, "total": 1, "top1_accuracy": 1.0},
                },
                "results": [
                    {
                        "task": "seeded_math_bug",
                        "strategy": "ast-symbol",
                        "selected_file": "src/math_utils.py",
                        "expected_file": "src/math_utils.py",
                        "hit": True,
                    }
                ],
            },
        )

        self.assertIn("AutoPR-Agent Experiments", output)
        self.assertIn("autopr-agent | 1/1 | 100%", output)
        self.assertIn("keyword-file | 0/1 | 0%", output)
        self.assertIn("src/math_utils.py", output)

    def test_status_reports_fixture_health(self) -> None:
        output = format_status(ROOT)

        self.assertIn("fixtures=ok", output)
        self.assertIn("dashboard=", output)

    def test_dashboard_renders_summary_and_diff(self) -> None:
        html = render_dashboard(
            {
                "created_at_utc": "20260101T000000Z",
                "summary": {
                    "autopr-agent": {
                        "solved": 1,
                        "total": 1,
                        "success_rate": 1.0,
                        "localized": 1,
                        "localization_rate": 1.0,
                    }
                },
                "metrics": [
                    {
                        "system": "autopr-agent",
                        "task": "seeded_math_bug",
                        "success": True,
                        "localized_expected_file": True,
                        "patch_changed_lines": 2,
                        "regression_failed_before_patch": True,
                        "tests_passed_after_patch": True,
                    }
                ],
                "details": [
                    {
                        "system": "autopr-agent",
                        "task": "seeded_math_bug",
                        "expected_file": "src/math_utils.py",
                        "selected_file": "src/math_utils.py",
                        "selected_symbol": "factorial",
                        "events": ["Patch applied"],
                        "patch_diff": "- return 0\n+ return 1",
                    }
                ],
            },
            {
                "summary": {"ast-symbol": {"hits": 1, "total": 1, "top1_accuracy": 1.0}},
                "results": [
                    {
                        "strategy": "ast-symbol",
                        "task": "seeded_math_bug",
                        "selected_file": "src/math_utils.py",
                        "expected_file": "src/math_utils.py",
                        "hit": True,
                    }
                ],
            },
        )

        self.assertIn("AutoPR-Agent Benchmark Dashboard", html)
        self.assertIn("src/math_utils.py", html)
        self.assertIn("- return 0", html)
        self.assertIn("Retrieval Ablation", html)


if __name__ == "__main__":
    unittest.main()
