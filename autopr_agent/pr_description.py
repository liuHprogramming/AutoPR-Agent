from __future__ import annotations

from pathlib import Path

from autopr_agent.formatting import normalize_diff_paths, relative_to_repo
from autopr_agent.models import RunState


def _status(value: bool) -> str:
    return "pass" if value else "fail"


def render_pr_description(state: RunState) -> str:
    title = state.analysis.title if state.analysis else state.issue_text
    patch_file = "not generated"
    test_file = "not generated"
    if state.patch_plan:
        patch_file = relative_to_repo(state.patch_plan.path, state.repo_path)
    if state.test_plan:
        test_file = relative_to_repo(state.test_plan.path, state.repo_path)

    before = state.verification_before.passed if state.verification_before else False
    after = state.verification_after.passed if state.verification_after else False
    risk = state.review.risk_level if state.review else "unknown"

    lines = [
        f"# Fix: {title}",
        "",
        "## Summary",
        f"- Issue: {state.issue_text}",
        f"- Patch target: `{patch_file}`",
        f"- Regression test: `{test_file}`",
        f"- Review risk: {risk}",
        "",
        "## Validation",
        f"- Regression failed before patch: {_status(before is False and state.verification_before is not None)}",
        f"- Tests passed after patch: {_status(after)}",
        f"- Patch applied: {_status(state.patch_applied)}",
        "",
        "## Agent Evidence",
    ]
    lines.extend(f"- {event}" for event in state.events)

    if state.review:
        lines.extend(["", "## Review Checklist"])
        lines.extend(f"- {name}: {_status(passed)}" for name, passed in state.review.checklist.items())
        if state.review.issues:
            lines.extend(["", "## Review Issues"])
            lines.extend(f"- {issue}" for issue in state.review.issues)

    if state.patch_plan:
        lines.extend([
            "",
            "## Patch Rationale",
            state.patch_plan.reason,
            "",
            "## Diff",
        ])
        if state.patch_diff:
            lines.extend(["```diff", normalize_diff_paths(state.patch_diff, state.repo_path), "```"])
        else:
            lines.append("No diff was recorded.")

    return "\n".join(lines) + "\n"


def write_pr_description(path: Path, state: RunState) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_pr_description(state), encoding="utf-8")
    return path
