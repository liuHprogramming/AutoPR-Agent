from __future__ import annotations

import argparse
from pathlib import Path


AGENT_FLOW = """```mermaid
flowchart TD
    Issue[Bug report] --> Understand[IssueUnderstandingAgent]
    Understand --> Search[CodeSearchAgent]
    Search --> Index[AST symbol index]
    Index --> Localize[BugLocalizationAgent]
    Localize --> Test[TestGenerationAgent]
    Test --> Before[VerifierAgent: before patch]
    Before --> Patch[PatchAgent]
    Patch --> Review[ReviewAgent]
    Review --> After[VerifierAgent: after patch]
    After --> Report[ReporterAgent]
    Report --> PR[Validated PR candidate]
```
"""

EVAL_FLOW = """```mermaid
flowchart TD
    Fixtures[Seeded benchmark fixtures] --> Guard[Fixture integrity guard]
    Guard --> Bench[Benchmark runner]
    Bench --> Compare[Single-agent vs AutoPR-Agent]
    Fixtures --> Ablation[Retrieval ablation]
    Ablation --> Strategies[Keyword file vs AST symbol ranking]
    Compare --> JSON[Benchmark JSON]
    Strategies --> AJSON[Ablation JSON]
    JSON --> Dashboard[Static dashboard]
    AJSON --> Dashboard
    JSON --> Summary[Project summary]
```
"""


def render_architecture_doc() -> str:
    lines = [
        "# AutoPR-Agent Architecture",
        "",
        "## Agent Repair Flow",
        "AutoPR-Agent decomposes code repair into specialized agents. The core guardrail is the test-first loop: generated regression tests must fail before the patch and pass after the patch.",
        "",
        AGENT_FLOW.strip(),
        "",
        "## Evaluation Flow",
        "The project evaluates both end-to-end repair quality and the retrieval/localization strategy. Reports are saved as JSON and rendered into a static dashboard.",
        "",
        EVAL_FLOW.strip(),
        "",
        "## Key Design Choices",
        "- Keep the default provider local and deterministic for repeatable evaluation.",
        "- Use AST symbol ranking to reduce test-file false positives.",
        "- Require before/after verification for accepted patches.",
        "- Record diffs, review checklists, and run artifacts for auditability.",
    ]
    return "\n".join(lines) + "\n"


def write_architecture_doc(root: Path) -> Path:
    output_path = root / "docs" / "ARCHITECTURE.md"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(render_architecture_doc(), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AutoPR-Agent architecture documentation")
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(write_architecture_doc(root))


if __name__ == "__main__":
    main()
