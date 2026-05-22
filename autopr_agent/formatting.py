from __future__ import annotations

from pathlib import Path


def relative_to_repo(path: Path, repo_path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_path.resolve()).as_posix()
    except ValueError:
        return path.name


def normalize_diff_paths(diff: str, repo_path: Path) -> str:
    if not diff:
        return diff
    normalized_lines: list[str] = []
    for line in diff.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            prefix, raw_path = line[:4], line[4:]
            normalized_lines.append(prefix + relative_to_repo(Path(raw_path), repo_path))
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)
