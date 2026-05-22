# AutoPR-Agent Experiments

## Purpose
The experiments test whether decomposing code repair into specialized agents improves validated bug-fix success over a compact single-agent baseline, and whether AST-symbol retrieval improves source-file localization over keyword file matching.

## End-to-End Repair Benchmark
System | Solved | Success rate | Localized expected file | Localization rate
--- | --- | --- | --- | ---
autopr-agent | 4/4 | 100% | 4/4 | 100%
single-agent | 0/4 | 0% | 0/4 | 0%

## Retrieval Ablation
Strategy | Top-1 hits | Top-1 accuracy
--- | --- | ---
ast-symbol | 4/4 | 100%
keyword-file | 0/4 | 0%

## Task-Level Repair Results
Task | System | Success | Selected source file | Patch changed lines | Before/after verification
--- | --- | --- | --- | --- | ---
seeded_math_bug | single-agent | False | False | 0 | fail
seeded_math_bug | autopr-agent | True | True | 2 | pass
seeded_text_bug | single-agent | False | False | 0 | fail
seeded_text_bug | autopr-agent | True | True | 2 | pass
seeded_list_bug | single-agent | False | False | 0 | fail
seeded_list_bug | autopr-agent | True | True | 8 | pass
seeded_dict_bug | single-agent | False | False | 0 | fail
seeded_dict_bug | autopr-agent | True | True | 4 | pass

## Task-Level Retrieval Results
Task | Strategy | Selected file | Expected file | Hit
--- | --- | --- | --- | ---
seeded_math_bug | keyword-file | tests/test_math_utils.py | src/math_utils.py | False
seeded_math_bug | ast-symbol | src/math_utils.py | src/math_utils.py | True
seeded_text_bug | keyword-file | tests/test_text_utils.py | src/text_utils.py | False
seeded_text_bug | ast-symbol | src/text_utils.py | src/text_utils.py | True
seeded_list_bug | keyword-file | tests/test_list_utils.py | src/list_utils.py | False
seeded_list_bug | ast-symbol | src/list_utils.py | src/list_utils.py | True
seeded_dict_bug | keyword-file | tests/test_dict_utils.py | src/dict_utils.py | False
seeded_dict_bug | ast-symbol | src/dict_utils.py | src/dict_utils.py | True

## Interpretation
The single-agent baseline is intentionally compact and uses the same local deterministic model family, but it often selects test files because keyword matching overweights files that mention the failing behavior. AutoPR-Agent adds AST symbol ranking, test-first validation, patch review, and before/after verification, which produces a measurable improvement on the seeded benchmark suite.
