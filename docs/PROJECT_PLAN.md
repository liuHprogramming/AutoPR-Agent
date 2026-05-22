# AutoPR-Agent Project Plan

## Project Background

Code repair is rarely a single-step generation task. A real bug-fix workflow usually includes reading a bug report, finding related files, identifying suspicious functions, writing a regression test, changing code, running checks, and preparing a reviewer-friendly PR summary.

AutoPR-Agent treats automated repair as an engineering workflow instead of a single prompt.

## Motivation

Single-agent coding assistants often fail in predictable ways:

- They retrieve irrelevant files and overload the context window.
- They patch before proving the bug with a failing test.
- They produce plausible but unverified fixes.
- They make broad edits that are hard to review.
- They cannot clearly explain which checks passed or failed.

The project motivation is to improve repair reliability by separating responsibilities across specialized agents and using tests as the main acceptance gate.

## Goal

Build a local-first multi-agent system that converts a bug report into a validated pull-request candidate.

The system should produce:

- structured issue analysis
- relevant file search results
- suspicious function localization
- generated regression test
- minimal patch
- before/after verification logs
- PR-style summary

## Main Improvement Target

Compared with a single all-in-one agent baseline, AutoPR-Agent should improve:

- validated patch success rate
- regression test validity
- bug localization precision
- patch minimality
- reviewer-facing report quality

## Phase 1: Local MVP

Status: in progress.

Scope:

- Python repositories only
- deterministic local model adapter
- seeded benchmark task
- multi-agent workflow
- CLI entry point
- unit test for before/after validation

## Phase 2: Real LLM Adapter

Add model providers behind the current adapter interface:

- OpenAI-compatible API
- Qwen or DeepSeek API
- optional local Ollama model

LLM-relevant techniques:

- structured JSON outputs
- function calling / tool calling
- prompt templates per agent role
- retry and validation logic

## Phase 3: Code RAG and Static Analysis

Improve code search and localization:

- AST-aware function/class chunking
- keyword + embedding hybrid retrieval
- import graph extraction
- call-site search
- context compression
- reranking

## Phase 4: Baseline Comparison

Implement baselines:

- single-agent baseline with the same tools
- retrieval-only patch agent
- full AutoPR-Agent workflow

Metrics:

- patch success rate
- regression test validity
- before-test fail rate
- after-test pass rate
- average repair iterations
- diff size
- runtime

## Phase 5: Dashboard

Build a demo UI:

- issue input
- agent trace
- retrieved files
- suspicious symbols
- generated test
- patch diff
- verification logs
- final PR summary
- benchmark metrics

Recommended stack:

- FastAPI backend
- Streamlit or React frontend
- SQLite run history

