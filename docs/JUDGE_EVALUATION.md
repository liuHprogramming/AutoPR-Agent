# AutoPR-Agent Judge Evaluation

## Scope
This labeled evaluation measures whether a patch-review judge approves valid PR candidates and rejects risky ones. The default report uses an offline deterministic heuristic judge for reproducibility. A live OpenAI-compatible judge can be evaluated with the same cases when an API key is available.

## Summary
- provider: heuristic-judge
- correct decisions: 11/12
- accuracy: 91.7%
- false approvals: 1
- false rejections: 0

## Case Results
Case | Category | Expected approval | Actual approval | Score | Correct
--- | --- | --- | --- | --- | ---
approve-factorial-edge-case | valid | True | True | 100 | True
approve-whitespace-normalization | valid | True | True | 100 | True
approve-order-preserving-dedup | valid | True | True | 100 | True
approve-default-merge | valid | True | True | 100 | True
reject-test-file-patch | targeting | False | False | 80 | True
reject-no-regression-test | test-quality | False | False | 80 | True
reject-patch-not-applied | application | False | False | 80 | True
reject-regression-passed-before | test-quality | False | False | 85 | True
reject-tests-fail-after | verification | False | False | 70 | True
reject-large-patch | minimality | False | False | 80 | True
reject-missing-patch | application | False | False | 60 | True
reject-semantic-mismatch | semantic | False | True | 100 | False

## Interpretation
The heuristic judge intentionally relies on structured validation evidence and review checks. The semantic-mismatch case demonstrates its limitation: a checklist can approve a syntactically small, test-passing patch even when the diff contradicts the issue. The optional LLM judge is intended to evaluate that semantic layer.
