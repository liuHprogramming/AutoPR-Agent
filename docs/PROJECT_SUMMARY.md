# AutoPR-Agent Project Summary

## Background
Software maintenance requires more than generating code from a prompt. A bug fix usually involves interpreting the issue, locating relevant code, writing a regression test, applying a minimal patch, running verification, and preparing reviewer-facing evidence.

## Motivation
Single-agent coding assistants often mix retrieval, reasoning, patching, and verification in one loop. In the seeded benchmark suite, the single-agent baseline repeatedly selects test files instead of source files, causing patch attempts to fail before validation.

## Goal
AutoPR-Agent aims to turn a bug report into a validated pull-request candidate using specialized agents for issue understanding, code search, AST-based localization, regression-test generation, patching, LLM-as-Judge-style review, verification, and reporting.

## Techniques
- Multi-agent workflow orchestration
- Provider-based LLM abstraction with local and OpenAI-compatible backends
- AST symbol indexing and symbol-ranking localization
- Test-first repair loop with before/after verification
- LLM-as-Judge-style patch review and risk scoring
- Patch diff tracking and changed-line metrics
- Benchmark, ablation, dashboard, and run-history artifacts

## Latest Results
- single-agent: 0/4 solved, 0/4 localized
- autopr-agent: 4/4 solved, 4/4 localized
- ast-symbol retrieval: 4/4 top-1 localization hits
- keyword-file retrieval: 0/4 top-1 localization hits

## CV Bullet
Built AutoPR-Agent, a multi-agent code repair system that converts bug reports into validated PR candidates using AST-based code localization, regression-test generation, patch synthesis, LLM-as-Judge-style review, and before/after test verification; on a seeded Python benchmark suite, improved validated repair success from 0/4 for a single-agent baseline to 4/4 and improved top-1 localization from 0/4 keyword retrieval to 4/4 AST-symbol ranking.
