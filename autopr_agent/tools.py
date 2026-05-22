from __future__ import annotations

import ast
import difflib
import subprocess
from dataclasses import dataclass
from pathlib import Path


IGNORED_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache"}


@dataclass
class FunctionDefInfo:
    name: str
    line: int
    source: str


@dataclass(frozen=True)
class SymbolInfo:
    name: str
    kind: str
    path: Path
    line: int
    end_line: int

    def to_dict(self, repo_path: Path) -> dict[str, str | int]:
        return {
            "name": self.name,
            "kind": self.kind,
            "path": self.path.relative_to(repo_path).as_posix(),
            "line": self.line,
            "end_line": self.end_line,
        }


@dataclass(frozen=True)
class ReplacementResult:
    applied: bool
    diff: str = ""
    changed_lines: int = 0


class RepoTools:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path.resolve()

    def python_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.repo_path.rglob("*.py"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            files.append(path)
        return sorted(files)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def search_terms(self, terms: list[str]) -> list[tuple[Path, int, list[str]]]:
        results: list[tuple[Path, int, list[str]]] = []
        lowered_terms = [term.lower() for term in terms if term]
        for path in self.python_files():
            text = self.read_text(path).lower()
            matched = [term for term in lowered_terms if term in text]
            if matched:
                score = sum(text.count(term) for term in matched)
                results.append((path, score, matched))
        return sorted(results, key=lambda item: item[1], reverse=True)

    def extract_functions(self, path: Path) -> list[FunctionDefInfo]:
        text = self.read_text(path)
        tree = ast.parse(text)
        lines = text.splitlines()
        functions: list[FunctionDefInfo] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                source = "\n".join(lines[node.lineno - 1 : end])
                functions.append(FunctionDefInfo(node.name, node.lineno, source))
        return sorted(functions, key=lambda item: item.line)


    def extract_symbols(self, path: Path) -> list[SymbolInfo]:
        text = self.read_text(path)
        tree = ast.parse(text)
        symbols: list[SymbolInfo] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="class",
                        path=path,
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="function",
                        path=path,
                        line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                    )
                )
        return sorted(symbols, key=lambda item: (str(item.path), item.line))

    def build_symbol_index(self) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        for path in self.python_files():
            symbols.extend(self.extract_symbols(path))
        return sorted(symbols, key=lambda item: (str(item.path), item.line, item.name))

    def apply_replacement(self, path: Path, original: str, replacement: str) -> ReplacementResult:
        text = self.read_text(path)
        if original not in text:
            return ReplacementResult(applied=False)
        updated = text.replace(original, replacement, 1)
        diff_lines = list(
            difflib.unified_diff(
                text.splitlines(),
                updated.splitlines(),
                fromfile=str(path),
                tofile=str(path),
                lineterm="",
            )
        )
        changed_lines = sum(
            1
            for line in diff_lines
            if (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---"))
        )
        self.write_text(path, updated)
        return ReplacementResult(
            applied=True,
            diff="\n".join(diff_lines),
            changed_lines=changed_lines,
        )

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=self.repo_path,
            text=True,
            capture_output=True,
            check=False,
        )

