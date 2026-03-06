"""
repo_parser.py - Repository Parser Module
==========================================
Parses entire code repositories, walks directory trees,
extracts source files, detects languages, and prepares
structured file manifests for the translation pipeline.
"""

import os
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


EXTENSION_MAP = {
    ".py": "python", ".java": "java", ".go": "go",
    ".rs": "rust",   ".js": "javascript", ".ts": "typescript",
    ".cpp": "cpp",   ".c": "c", ".cs": "csharp",
    ".rb": "ruby",   ".kt": "kotlin", ".swift": "swift",
}

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", "target", ".idea", ".vscode",
}

DEPENDENCY_FILES = {
    "requirements.txt", "Cargo.toml", "go.mod",
    "pom.xml", "package.json", "build.gradle",
}


@dataclass
class SourceFile:
    path: str
    language: str
    size_bytes: int
    sha256: str
    content: str
    import_lines: list = field(default_factory=list)
    exported_symbols: list = field(default_factory=list)


@dataclass
class RepoManifest:
    repo_root: str
    primary_language: str
    total_files: int
    total_bytes: int
    files: list = field(default_factory=list)
    dependency_files: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class RepoParser:
    """Walk a local repository and produce a RepoManifest."""

    def __init__(self, repo_root: str, target_language: Optional[str] = None):
        self.repo_root = Path(repo_root).resolve()
        self.target_language = target_language

    def parse(self) -> "RepoManifest":
        source_files, dep_files, lang_counts = [], [], {}
        for dirpath, dirnames, filenames in os.walk(self.repo_root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                full = Path(dirpath) / fname
                rel = str(full.relative_to(self.repo_root))
                if fname in DEPENDENCY_FILES:
                    dep_files.append(rel)
                    continue
                lang = EXTENSION_MAP.get(full.suffix.lower())
                if not lang:
                    continue
                if self.target_language and lang != self.target_language:
                    continue
                sf = self._parse_file(full, rel, lang)
                source_files.append(sf)
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        primary = max(lang_counts, key=lang_counts.get) if lang_counts else "unknown"
        return RepoManifest(
            repo_root=str(self.repo_root),
            primary_language=primary,
            total_files=len(source_files),
            total_bytes=sum(f.size_bytes for f in source_files),
            files=source_files,
            dependency_files=dep_files,
            metadata={"language_distribution": lang_counts},
        )

    def _parse_file(self, full: "Path", rel: str, lang: str) -> "SourceFile":
        raw = full.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        return SourceFile(
            path=rel,
            language=lang,
            size_bytes=len(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            content=content,
            import_lines=self._extract_imports(content, lang),
            exported_symbols=self._extract_symbols(content, lang),
        )

    @staticmethod
    def _extract_imports(content: str, lang: str) -> list:
        import re
        patterns = {
            "python": r"^(?:import|from)\s+\S+",
            "java":   r"^import\s+[\w.]+",
            "go":     r'^import\s+"[^"]+"',
            "rust":   r"^use\s+[\w:]+",
        }
        return re.findall(patterns.get(lang, r"^import\s+"), content, re.MULTILINE)

    @staticmethod
    def _extract_symbols(content: str, lang: str) -> list:
        import re
        patterns = {
            "python": [r"^class\s+(\w+)", r"^def\s+(\w+)"],
            "java":   [r"public\s+class\s+(\w+)"],
            "go":     [r"^func\s+(\w+)", r"^type\s+(\w+)"],
            "rust":   [r"^pub\s+fn\s+(\w+)", r"^pub\s+struct\s+(\w+)"],
        }
        syms = []
        for pat in patterns.get(lang, []):
            syms.extend(re.findall(pat, content, re.MULTILINE))
        return syms


def parse_repo(repo_path: str, language_filter: Optional[str] = None) -> dict:
    """Public API for the pipeline orchestrator."""
    return asdict(RepoParser(repo_path, language_filter).parse())


if __name__ == "__main__":
    import sys, pprint
    result = parse_repo(sys.argv[1] if len(sys.argv) > 1 else ".")
    pprint.pprint({k: v for k, v in result.items() if k != "files"})
    print(f"Parsed {result['total_files']} files ({result['total_bytes']:,} bytes)")
