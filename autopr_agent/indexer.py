from __future__ import annotations

import argparse
import json
from pathlib import Path

from autopr_agent.tools import RepoTools


def build_index(repo_path: Path) -> list[dict[str, str | int]]:
    tools = RepoTools(repo_path)
    return [symbol.to_dict(tools.repo_path) for symbol in tools.build_symbol_index()]


def format_index(index: list[dict[str, str | int]]) -> str:
    lines = ["kind | name | path | line", "--- | --- | --- | ---"]
    for item in index:
        lines.append(f"{item['kind']} | {item['name']} | {item['path']} | {item['line']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an AST symbol index for a Python repository")
    parser.add_argument("repo", type=Path)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args()
    index = build_index(args.repo)
    if args.json:
        print(json.dumps(index, indent=2))
    else:
        print(format_index(index))


if __name__ == "__main__":
    main()
