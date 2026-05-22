# Development Guide

This project is intentionally lightweight: the default demo and evaluation use a deterministic local provider, so no API key or heavy compute is required.

## Environment

Requires Python 3.11 or newer.

Optional editable install:

```bash
python3 -m pip install -e .
```

## Core Checks

Run the unit test suite:

```bash
python3 -m unittest discover tests
```

Check demo readiness:

```bash
python3 -m autopr_agent.status
```

Run the same deterministic evaluation used for the project results:

```bash
python3 -m autopr_agent.evaluate
```

## Demo Artifacts

Run a one-command seeded demo:

```bash
python3 -m autopr_agent demo math
```

Generate local demo artifacts:

```bash
python3 -m autopr_agent demo math \
  --report-out runs/demo-report.md \
  --pr-out runs/PR_DESCRIPTION.md
```

Generate stable example artifacts that are suitable for GitHub readers:

```bash
python3 -m autopr_agent.examples
```

## Documentation Artifacts

Regenerate project docs:

```bash
python3 -m autopr_agent.project_summary
python3 -m autopr_agent.architecture_doc
python3 -m autopr_agent.benchmark_catalog
python3 -m autopr_agent.experiments_doc
python3 -m autopr_agent.dashboard
```

## CI-Equivalent Local Run

This approximates the GitHub Actions workflow:

```bash
python3 -m unittest discover tests
python3 -m autopr_agent.status
python3 -m autopr_agent.evaluate
python3 -m autopr_agent.project_summary
python3 -m autopr_agent.architecture_doc
python3 -m autopr_agent.benchmark_catalog
python3 -m autopr_agent.examples
python3 -m autopr_agent.experiments_doc
```

## Benchmark Fixture Safety

Benchmark fixtures under `benchmarks/*/repo` should remain intentionally buggy. Use `--workdir-copy` or the `demo` command when running repair workflows so the fixtures are not mutated.
