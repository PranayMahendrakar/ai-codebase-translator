"""
pipeline.py - Translation Pipeline Orchestrator
=================================================
Ties together all five stages of the AI Codebase Translator:

    repo_parser -> ast_generator -> language_mapping_engine
                -> code_generator -> test_runner

Usage:
    python pipeline.py --input ./my_python_project --source python --target rust --output ./translated
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict

from repo_parser import parse_repo, RepoManifest
from ast_generator import generate_ast
from language_mapping_engine import create_mapping_engine
from code_generator import generate_code
from test_runner import run_tests


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------
@dataclass
class TranslationConfig:
    input_path: str
    source_language: str
    target_language: str
    output_path: str
    run_tests: bool = True
    verbose: bool = False
    max_files: int = 500          # safety limit
    preserve_structure: bool = True


@dataclass
class TranslationResult:
    config: TranslationConfig
    files_parsed: int = 0
    files_translated: int = 0
    files_failed: int = 0
    test_results: dict = field(default_factory=dict)
    total_time_s: float = 0.0
    translated_files: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.files_parsed
        return (self.files_translated / total * 100) if total else 0.0

    def summary(self) -> str:
        return (
            f"Translation Summary\n"
            f"==================\n"
            f"Source:      {self.config.source_language}  ({self.config.input_path})\n"
            f"Target:      {self.config.target_language}  ({self.config.output_path})\n"
            f"Files:       {self.files_parsed} parsed, {self.files_translated} translated, {self.files_failed} failed\n"
            f"Success:     {self.success_rate:.1f}%\n"
            f"Time:        {self.total_time_s:.2f}s\n"
            f"Tests:       {self.test_results.get('passed', 0)}/{self.test_results.get('total', 0)} passed\n"
        )


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------
class TranslationPipeline:

    def __init__(self, config: TranslationConfig):
        self.config = config
        self.engine = create_mapping_engine(config.source_language, config.target_language)

    # ------------------------------------------------------------------
    def run(self) -> TranslationResult:
        result = TranslationResult(config=self.config)
        start = time.perf_counter()

        try:
            # Stage 1: Parse repository
            self._log("Stage 1/5: Parsing repository...")
            manifest = self._stage_parse()
            result.files_parsed = manifest["total_files"]

            # Stage 2-4: Translate each file
            self._log(f"Stage 2-4: Translating {result.files_parsed} files...")
            translated_sources = self._stage_translate(manifest, result)

            # Stage 5: Run tests
            if self.config.run_tests and translated_sources:
                self._log("Stage 5/5: Running tests...")
                result.test_results = self._stage_test(translated_sources)
            else:
                self._log("Stage 5/5: Skipping tests.")

        except Exception as e:
            result.errors.append(str(e))
            self._log(f"Pipeline error: {e}", level="ERROR")

        result.total_time_s = time.perf_counter() - start
        return result

    # ------------------------------------------------------------------
    def _stage_parse(self) -> dict:
        """Stage 1: repo_parser."""
        return parse_repo(self.config.input_path, self.config.source_language)

    def _stage_translate(self, manifest: dict, result: TranslationResult) -> list[dict]:
        """Stages 2-4: ast_generator + language_mapping_engine + code_generator."""
        translated = []
        output_base = Path(self.config.output_path)
        output_base.mkdir(parents=True, exist_ok=True)

        for file_info in manifest.get("files", [])[: self.config.max_files]:
            src_path = file_info["path"]
            src_content = file_info["content"]

            try:
                # Stage 2: AST generation (IR)
                ir_dict = generate_ast(src_content, self.config.source_language)

                # Stage 3: Language mapping (no separate call needed - part of code_generator)
                # Stage 4: Code generation
                from ast_generator import IRNode, NodeKind
                # Reconstruct minimal IR for code generator
                ir = self._dict_to_ir(ir_dict)
                translated_code = generate_code(ir, self.config.source_language, self.config.target_language)

                # Write output file
                out_path = self._compute_output_path(src_path)
                out_file = output_base / out_path
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(translated_code, encoding="utf-8")

                translated.append({
                    "source_path": src_path,
                    "output_path": str(out_file),
                    "source_code": src_content,
                    "target_code": translated_code,
                })
                result.files_translated += 1
                result.translated_files.append(str(out_path))
                self._log(f"  [OK] {src_path} -> {out_path}")

            except Exception as e:
                result.files_failed += 1
                result.errors.append(f"{src_path}: {e}")
                self._log(f"  [FAIL] {src_path}: {e}", level="WARN")

        return translated

    def _stage_test(self, translated_sources: list[dict]) -> dict:
        """Stage 5: test_runner."""
        all_results = {"total": 0, "passed": 0, "failed": 0, "details": []}
        for item in translated_sources[:10]:  # test first 10 files
            tr = run_tests(
                source_code=item["source_code"],
                target_code=item["target_code"],
                source_lang=self.config.source_language,
                target_lang=self.config.target_language,
                module_name=Path(item["source_path"]).stem,
            )
            all_results["total"]  += tr["total"]
            all_results["passed"] += tr["passed"]
            all_results["failed"] += tr["failed"]
            all_results["details"].append(tr)
        return all_results

    # ------------------------------------------------------------------
    def _compute_output_path(self, src_path: str) -> str:
        ext_map = {
            "rust":       ".rs",
            "go":         ".go",
            "java":       ".java",
            "typescript": ".ts",
            "javascript": ".js",
            "python":     ".py",
        }
        ext = ext_map.get(self.config.target_language, ".txt")
        p = Path(src_path)
        return str(p.with_suffix(ext))

    def _dict_to_ir(self, ir_dict: dict):
        """Reconstruct a minimal IRNode tree from a serialised dict."""
        from ast_generator import IRNode, NodeKind
        kind_str = ir_dict.get("kind", "module")
        try:
            kind = NodeKind(kind_str)
        except ValueError:
            kind = NodeKind.UNKNOWN
        node = IRNode(
            kind=kind,
            name=ir_dict.get("name"),
            value=ir_dict.get("value"),
        )
        for child_dict in ir_dict.get("children", []):
            node.children.append(self._dict_to_ir(child_dict))
        return node

    def _log(self, msg: str, level: str = "INFO"):
        if self.config.verbose or level in ("WARN", "ERROR"):
            print(f"[{level}] {msg}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="AI Codebase Translator - translate entire repos between languages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Translate a Python project to Rust
  python pipeline.py --input ./my_app --source python --target rust --output ./my_app_rs

  # Translate Java to Go with tests disabled
  python pipeline.py --input ./java_app --source java --target go --output ./go_app --no-tests

  # Verbose mode
  python pipeline.py --input ./app --source python --target go --output ./app_go -v
""",
    )
    p.add_argument("--input",  "-i", required=True, help="Path to source repository")
    p.add_argument("--source", "-s", required=True,
                   choices=["python", "java", "go", "rust", "javascript", "typescript"],
                   help="Source programming language")
    p.add_argument("--target", "-t", required=True,
                   choices=["python", "java", "go", "rust", "javascript", "typescript"],
                   help="Target programming language")
    p.add_argument("--output", "-o", required=True, help="Output directory for translated code")
    p.add_argument("--no-tests",    action="store_true", help="Skip test generation and execution")
    p.add_argument("--max-files",   type=int, default=500, help="Maximum files to translate")
    p.add_argument("--json",        action="store_true", help="Output results as JSON")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return p


def main():
    args = build_parser().parse_args()
    config = TranslationConfig(
        input_path=args.input,
        source_language=args.source,
        target_language=args.target,
        output_path=args.output,
        run_tests=not args.no_tests,
        verbose=args.verbose,
        max_files=args.max_files,
    )

    print(f"AI Codebase Translator")
    print(f"  {config.source_language} -> {config.target_language}")
    print(f"  {config.input_path} -> {config.output_path}")
    print()

    pipeline = TranslationPipeline(config)
    result = pipeline.run()

    if args.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print(result.summary())
        if result.errors:
            print("Errors:")
            for err in result.errors[:10]:
                print(f"  - {err}")

    sys.exit(0 if result.files_failed == 0 else 1)


if __name__ == "__main__":
    main()
