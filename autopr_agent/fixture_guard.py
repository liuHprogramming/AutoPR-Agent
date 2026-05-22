from __future__ import annotations

from pathlib import Path


EXPECTED_BUG_SNIPPETS = {
    "seeded_math_bug": ("src/math_utils.py", "if n == 0:\n        return 0"),
    "seeded_text_bug": ("src/text_utils.py", "return text.strip()"),
    "seeded_list_bug": ("src/list_utils.py", "return sorted(set(items))"),
    "seeded_dict_bug": ("src/dict_utils.py", "return overrides.copy()"),
}

GENERATED_TEST_PREFIXES = (
    "test_factorial_regression.py",
    "test_whitespace_regression.py",
    "test_unique_order_regression.py",
    "test_merge_defaults_regression.py",
    "test_regression.py",
)


def fixture_integrity_errors(root: Path) -> list[str]:
    errors: list[str] = []
    benchmarks_dir = root / "benchmarks"
    for name, (relative_file, expected_snippet) in EXPECTED_BUG_SNIPPETS.items():
        repo = benchmarks_dir / name / "repo"
        target = repo / relative_file
        if not target.exists():
            errors.append(f"{name}: missing {relative_file}")
            continue
        if expected_snippet not in target.read_text(encoding="utf-8"):
            errors.append(f"{name}: expected buggy snippet missing from {relative_file}")
        generated_tests = [path for path in (repo / "tests").glob("test_*.py") if path.name in GENERATED_TEST_PREFIXES]
        for path in generated_tests:
            errors.append(f"{name}: generated regression test left in fixture: {path.name}")
    return errors
