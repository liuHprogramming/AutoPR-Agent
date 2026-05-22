# AutoPR-Agent Benchmark Catalog

The seeded benchmark suite is designed to evaluate whether AutoPR-Agent can move from a natural-language bug report to a validated patch while avoiding the common failure mode of patching or over-weighting test files.

## Tasks
Task | Category | Expected source file | Seeded bug | Expected repair
--- | --- | --- | --- | ---
seeded_math_bug | numeric edge case | `src/math_utils.py` | factorial(0) returns 0 instead of 1 | return 1 for the zero case
seeded_text_bug | string normalization | `src/text_utils.py` | normalize_whitespace strips outer whitespace but keeps repeated internal spaces | split and rejoin text so repeated whitespace collapses to one space
seeded_list_bug | list ordering | `src/list_utils.py` | unique_preserve_order removes duplicates by sorting, which changes first-seen order | track seen values and append each new item once
seeded_dict_bug | dictionary merge semantics | `src/dict_utils.py` | merge_defaults returns only overrides and drops default-only keys | copy defaults, then update them with overrides

## Why These Tasks
- seeded_math_bug: Tests whether the repair loop can localize a small boundary-condition bug.
- seeded_text_bug: Tests whether generated regression tests capture behavior beyond the existing tests.
- seeded_list_bug: Tests whether patching preserves semantic ordering instead of only satisfying uniqueness.
- seeded_dict_bug: Tests whether the workflow handles stateful data-structure behavior beyond scalars and strings.

## Evaluation Contract
A successful AutoPR-Agent run must localize the expected source file, generate a regression test that fails before the patch, apply a minimal source patch, pass tests after the patch, and pass the review checklist.
