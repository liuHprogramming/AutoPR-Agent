from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from autopr_agent.pr_description import render_pr_description
from autopr_agent.workflow import AutoPRWorkflow

EXAMPLE_ISSUE = "factorial(0) returns 0, but mathematically it should return 1"
EXAMPLE_REPO = Path("benchmarks/seeded_math_bug/repo")


def render_example_readme() -> str:
    return """# AutoPR-Agent Examples

This folder contains stable sample outputs that can be inspected without running the project first.

- `PR_DESCRIPTION.md`: concise PR-style artifact generated from the seeded math demo.
- `RUN_REPORT.md`: fuller agent trace and patch report from the same demo.

Regenerate these files from the repository root with:

```bash
python3 -m autopr_agent.examples
```
"""


def generate_example_artifacts(root: Path) -> list[Path]:
    examples_dir = root / "examples"
    examples_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = Path(tmpdir) / "repo"
        shutil.copytree(root / EXAMPLE_REPO, repo)
        state, report = AutoPRWorkflow(repo).run(EXAMPLE_ISSUE)
        artifacts = {
            "README.md": render_example_readme(),
            "PR_DESCRIPTION.md": render_pr_description(state),
            "RUN_REPORT.md": report + "\n",
        }
        written: list[Path] = []
        for name, content in artifacts.items():
            output_path = examples_dir / name
            output_path.write_text(content, encoding="utf-8")
            written.append(output_path)
        return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate stable AutoPR-Agent example artifacts")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for path in generate_example_artifacts(root):
        print(path)


if __name__ == "__main__":
    main()
