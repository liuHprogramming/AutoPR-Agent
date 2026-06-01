# AutoPR-Agent

AutoPR-Agent is a multi-agent code repair prototype that turns a bug report into a validated pull-request candidate. It splits repair into specialized agents for issue understanding, code search, AST-based localization, regression-test generation, patch synthesis, review, verification, and PR-style reporting.

## Results Snapshot

| System / strategy | Result |
| --- | --- |
| Single-agent repair baseline | 0/4 bugs solved, 0/4 localized |
| AutoPR-Agent multi-agent workflow | 4/4 bugs solved, 4/4 localized |
| Keyword-file retrieval | 0/4 top-1 localization hits |
| AST-symbol retrieval | 4/4 top-1 localization hits |

Why it matters: the single-agent baseline repeatedly selects test files instead of source files. AutoPR-Agent improves the workflow with AST symbol ranking, test-first validation, patch review, and before/after verification.

## Quick Demo

Run a seeded live demo without needing an API key:

```bash
python3 -m autopr_agent demo math
```

Save the generated full run report and concise PR description:

```bash
python3 -m autopr_agent demo math \
  --report-out runs/demo-report.md \
  --pr-out runs/PR_DESCRIPTION.md
```

Run the full deterministic evaluation pipeline:

```bash
python3 -m autopr_agent.evaluate
```

## What This Demonstrates

- Multi-agent workflow orchestration for code repair
- LLM-style provider abstraction with local and OpenAI-compatible backends
- AST symbol indexing and source-file localization
- Regression-test generation with before/after verification
- Patch synthesis, review checklists, risk labels, and diff tracking
- Baseline comparison, retrieval ablation, dashboard, CI, and reproducible reports

## Generated Artifacts

- [Project summary](docs/PROJECT_SUMMARY.md)
- [Architecture diagrams](docs/ARCHITECTURE.md)
- [Benchmark catalog](docs/BENCHMARKS.md)
- [Experiment results](docs/EXPERIMENTS.md)
- [Static dashboard](runs/dashboard.html)
- [Demo run report](runs/demo-report.md)
- [Generated PR description](runs/PR_DESCRIPTION.md)
- [Stable example outputs](examples/README.md)

## Repository Guide

- [Development guide](DEVELOPMENT.md)
- [License](LICENSE)
- [Stable example outputs](examples/README.md)
- [GitHub Actions workflow](.github/workflows/ci.yml)

## Background

Modern software teams spend a lot of time on repetitive maintenance work: reading bug reports, finding faulty code, writing regression tests, creating minimal patches, running checks, and preparing PR summaries. Existing coding assistants can help with individual steps, but real bug fixing is a workflow rather than a single prompt.

## Motivation

Single-agent coding systems often mix too many responsibilities. They may retrieve irrelevant files, patch code without proving the bug, ignore edge cases, produce broad diffs, or fail to recover from test errors.

AutoPR-Agent improves reliability by splitting the repair process into specialized agents:

- Issue understanding
- Code search
- Bug localization with AST symbol ranking
- Regression test generation
- Patch synthesis
- Review
- Verification
- PR reporting

## Goal

Given a repository path and a bug report, AutoPR-Agent should produce:

- a structured issue summary
- relevant files and suspicious symbols
- a regression test
- a minimal code patch
- test and lint results
- a PR-style summary with risks and evidence

The main evaluation target is validated patch success rate compared with a single-agent baseline.

## MVP Status

This repository starts with a local deterministic MVP:

- no API key required for the default local model
- OpenAI-compatible provider scaffold for future real LLM calls
- Python-only seeded benchmarks covering math, text, and list utilities
- multi-agent workflow orchestration
- tool wrappers for file search, AST symbol indexing, patching, and tests
- CLI demo
- fixture integrity guard to catch accidental benchmark mutation

Later versions can replace the deterministic model with OpenAI, Claude, Qwen, DeepSeek, or a local Ollama model.

## Usage

Run directly from the source tree:

```bash
python3 -m autopr_agent run benchmarks/seeded_math_bug/repo \
  --issue "factorial(0) returns 0, but mathematically it should return 1" \
  --provider local \
  --workdir-copy
```

After installing the package, the same workflow is available as a console command:

```bash
autopr-agent run benchmarks/seeded_math_bug/repo \
  --issue "factorial(0) returns 0, but mathematically it should return 1" \
  --provider local \
  --workdir-copy
```

Optional OpenAI-compatible provider scaffold:

```bash
OPENAI_API_KEY=... python3 -m autopr_agent run benchmarks/seeded_math_bug/repo \
  --issue "factorial(0) returns 0, but mathematically it should return 1" \
  --provider openai-compatible \
  --model gpt-4.1-mini
```

Run the test suite:

```bash
python3 -m unittest discover tests
```

The repository also includes a GitHub Actions workflow at `.github/workflows/ci.yml` that runs tests, checks demo readiness, runs deterministic evaluation, and regenerates documentation artifacts on push or pull request.

Run only the local benchmark without mutating the benchmark fixtures. This also writes a timestamped JSON report under `runs/`:

```bash
python3 -m autopr_agent.benchmark
```

Summarize the latest benchmark report:

```bash
python3 -m autopr_agent.report
```

List benchmark run history:

```bash
python3 -m autopr_agent.history
```

Check demo readiness status:

```bash
python3 -m autopr_agent.status
```

Generate a recruiter/GitHub-ready project summary:

```bash
python3 -m autopr_agent.project_summary
```

Generate architecture documentation with Mermaid diagrams:

```bash
python3 -m autopr_agent.architecture_doc
```

Generate the benchmark catalog:

```bash
python3 -m autopr_agent.benchmark_catalog
```

Generate stable example outputs for GitHub readers:

```bash
python3 -m autopr_agent.examples
```

Generate experiment documentation from the latest benchmark and ablation reports:

```bash
python3 -m autopr_agent.experiments_doc
```

Generate a static HTML dashboard from the latest report:

```bash
python3 -m autopr_agent.dashboard
```

Build an AST symbol index for a target repo:

```bash
python3 -m autopr_agent.indexer benchmarks/seeded_math_bug/repo
```

Compare keyword retrieval against AST symbol ranking. This writes a timestamped ablation JSON report under `runs/`:

```bash
python3 -m autopr_agent.ablation
```

## Architecture

```text
IssueUnderstandingAgent
        |
CodeSearchAgent
        |
BugLocalizationAgent
        |
TestGenerationAgent
        |
PatchAgent <---- ReviewAgent
        |              |
VerifierAgent --------+
        |
ReporterAgent
```

## Evaluation

Baselines:

- single all-in-one agent with the same tools
- retrieval-only patch agent
- full multi-agent workflow

Current benchmark output compares:

- `single-agent`: compact all-in-one repair baseline
- `autopr-agent`: role-separated workflow with regression-test validation and review

Metrics, agent trace and selected-file details are printed to the terminal and saved as JSON for later comparison.

Metrics:

- patch success rate
- bug localization accuracy
- retrieval strategy top-1 accuracy
- regression test validity
- existing test pass rate
- number of repair iterations
- diff size
- patch changed-line count
- review rejection rate
- runtime
