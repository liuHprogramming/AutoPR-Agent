# Fix: factorial(0) returns 0, but mathematically it should return 1

## Summary
- Issue: factorial(0) returns 0, but mathematically it should return 1
- Patch target: `src/math_utils.py`
- Regression test: `tests/test_factorial_regression.py`
- Review risk: low

## Validation
- Regression failed before patch: pass
- Tests passed after patch: pass
- Patch applied: pass

## Agent Evidence
- Issue analyzed: factorial(0) returns 0, but mathematically it should return 1
- Code search found 2 candidate files after indexing 4 symbols
- Localized 3 suspicious symbols via AST symbol ranking
- Regression test written: test_factorial_regression.py
- Regression test failed before patch as expected
- Patch applied with 2 changed lines
- Tests passed after patch
- Review approved patch with low risk; judge=heuristic-judge score=100

## Review Checklist
- patch_generated: pass
- patch_applied: pass
- regression_test_generated: pass
- patch_targets_source: pass
- patch_is_minimal: pass

## LLM-as-Judge
Provider: heuristic-judge
Approved: pass
Score: 100
Rationale: Patch is approved because it targets source code, includes a regression test, fails before the patch, passes after the patch, and remains minimal.

## Patch Rationale
factorial(0) is defined as 1.

## Diff
```diff
--- src/math_utils.py
+++ src/math_utils.py
@@ -2,7 +2,7 @@
     if n < 0:
         raise ValueError("factorial is undefined for negative numbers")
     if n == 0:
-        return 0
+        return 1
     result = 1
     for value in range(1, n + 1):
         result *= value
```
