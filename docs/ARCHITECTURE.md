# AutoPR-Agent Architecture

## Agent Repair Flow
AutoPR-Agent decomposes code repair into specialized agents. The core guardrail is the test-first loop: generated regression tests must fail before the patch and pass after the patch.

```mermaid
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

## Evaluation Flow
The project evaluates both end-to-end repair quality and the retrieval/localization strategy. Reports are saved as JSON and rendered into a static dashboard.

```mermaid
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

## Key Design Choices
- Keep the default provider local and deterministic for repeatable evaluation.
- Use AST symbol ranking to reduce test-file false positives.
- Require before/after verification for accepted patches.
- Record diffs, review checklists, and run artifacts for auditability.
