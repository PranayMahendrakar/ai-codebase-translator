# AI Codebase Translator

> **Automatically convert entire codebases between programming languages — preserving architecture, translating dependencies, and generating unit tests.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Pages](https://img.shields.io/badge/demo-GitHub%20Pages-brightgreen)](https://pranayMahendrakar.github.io/ai-codebase-translator)

---

## Overview

AI Codebase Translator is a multi-stage pipeline that converts **entire repositories** from one programming language to another. It goes beyond simple syntax translation by understanding the *semantics* of each language and mapping to idiomatic constructs.

### Supported Conversions

| From | To |
|------|-----|
| Python | Rust |
| Python | Go |
| Python | TypeScript |
| Java | Go |
| Java | Rust |
| Java | TypeScript |

---

## Translation Architecture

The pipeline consists of five stages:

```
Input Repo
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1 │  repo_parser.py                                      │
│          │  Walk directory tree, detect languages, extract       │
│          │  source files, imports, and exported symbols          │
└──────────┴──────────────────┬──────────────────────────────────┘
                              │  RepoManifest (list of SourceFile)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2 │  ast_generator.py                                    │
│          │  Convert source to language-agnostic IR (IRNode tree) │
│          │  Full Python AST; regex heuristics for Java/Go/Rust  │
└──────────┴──────────────────┬──────────────────────────────────┘
                              │  IRNode tree
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3 │  language_mapping_engine.py                          │
│          │  Map IR types, stdlib, deps, and idioms to target     │
│          │  Handles: Python int→Rust i64, list comp→iterator    │
└──────────┴──────────────────┬──────────────────────────────────┘
                              │  MappingEngine + IdiomRules
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4 │  code_generator.py                                   │
│          │  Walk IR tree and emit target-language source code    │
│          │  Applies idioms, naming conventions, ownership model  │
└──────────┴──────────────────┬──────────────────────────────────┘
                              │  Translated source files
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5 │  test_runner.py                                      │
│          │  Generate unit tests from function signatures         │
│          │  Execute source + target, compare outputs             │
└──────────┴─────────────────────────────────────────────────────┘
                              │
                              ▼
                      Translation Report
```

### Architecture Preservation

The translator preserves your original codebase structure:

- **Module / package boundaries** → Equivalent directory layout in the target language
- **Class hierarchies** → Structs + impls (Rust), types + methods (Go), or classes (Java)
- **Dependency graph** → Remapped to target-language package managers (PyPI → crates.io → pkg.go.dev)
- **Visibility modifiers** → public/private/protected semantics mapped across languages
- **Documentation** → Docstrings → doc comments (`///` in Rust, `//` in Go)

---

## Installation

```bash
git clone https://github.com/PranayMahendrakar/ai-codebase-translator
cd ai-codebase-translator
pip install -r requirements.txt
```

---

## Usage

### CLI

```bash
# Translate a Python project to Rust
python src/pipeline.py --input ./my_python_app --source python --target rust --output ./my_rust_app

# Translate Java to Go
python src/pipeline.py --input ./java_service --source java --target go --output ./go_service

# With verbose output and JSON report
python src/pipeline.py --input ./app --source python --target go --output ./app_go --verbose --json
```

### Programmatic API

```python
from src.pipeline import TranslationPipeline, TranslationConfig

config = TranslationConfig(
    input_path="./my_app",
    source_language="python",
    target_language="rust",
    output_path="./my_app_rs",
    run_tests=True,
    verbose=True,
)

result = TranslationPipeline(config).run()
print(result.summary())
# => Files: 42 parsed, 40 translated, 2 failed
# => Success: 95.2%
# => Tests: 87/91 passed
```

---

## Pipeline Modules

| Module | Responsibility |
|--------|---------------|
| `src/repo_parser.py` | Walk repo, detect languages, extract file metadata |
| `src/ast_generator.py` | Parse source → language-agnostic IR (IRNode tree) |
| `src/language_mapping_engine.py` | Type/stdlib/idiom mappings between language pairs |
| `src/code_generator.py` | IR → target-language source code emitter |
| `src/test_runner.py` | Auto-generate and execute unit tests, produce report |
| `src/pipeline.py` | CLI + orchestrator that chains all five stages |

---

## Idiom Translations

### Python → Rust

| Python | Rust |
|--------|------|
| `[x*2 for x in nums if x>0]` | `nums.iter().filter(\|&&x\| x>0).map(\|&x\| x*2).collect::<Vec<_>>()` |
| `with open(p) as f: data=f.read()` | `let data = fs::read_to_string(p)?;` |
| `try: ... except E as e: ...` | `match risky() { Ok(v)=>use(v), Err(e)=>handle(e) }` |
| `Optional[T]` | `Option<T>` |
| `Dict[K, V]` | `HashMap<K, V>` |

### Python → Go

| Python | Go |
|--------|----|
| `[x for x in items if cond]` | `for _, x := range items { if cond { result = append(...) } }` |
| `class Foo:` | `type Foo struct { ... }` |
| `raise ValueError(msg)` | `return nil, errors.New(msg)` |
| `Optional[T]` | `*T` (pointer) |
| `Dict[K, V]` | `map[K]V` |

---

## Dependency Mapping

### Python → Rust (crates.io)

| Python (PyPI) | Rust (crates.io) |
|---------------|-----------------|
| requests | reqwest |
| numpy | ndarray |
| pandas | polars |
| flask | axum / actix-web |
| sqlalchemy | diesel |
| pydantic | serde |
| pytest | cargo test (built-in) |

### Python → Go (pkg.go.dev)

| Python (PyPI) | Go |
|---------------|----|
| requests | net/http (stdlib) |
| flask | gin / echo |
| sqlalchemy | gorm |
| pytest | testing (stdlib) |
| pydantic | encoding/json + validator |

---

## Benchmarks

See the [GitHub Pages demo](https://pranayMahendrakar.github.io/ai-codebase-translator) for interactive before/after comparisons and performance benchmarks.

### Translation Performance (sample project: 100 files)

| Stage | Time |
|-------|------|
| repo_parser | ~0.1s |
| ast_generator | ~0.8s |
| language_mapping_engine | ~0.05s |
| code_generator | ~1.2s |
| test_runner | ~4.5s |
| **Total** | **~6.6s** |

### Runtime Benchmarks (Fibonacci, n=35)

| Language | Time |
|----------|------|
| Python | 2,340 ms |
| Go | 48 ms (49x faster) |
| Rust | 12 ms (195x faster) |

---

## Project Structure

```
ai-codebase-translator/
├── src/
│   ├── repo_parser.py             # Stage 1: Repository parser
│   ├── ast_generator.py           # Stage 2: AST / IR generator
│   ├── language_mapping_engine.py # Stage 3: Language mapping
│   ├── code_generator.py          # Stage 4: Code emitter
│   ├── test_runner.py             # Stage 5: Test generator & runner
│   └── pipeline.py                # Orchestrator + CLI
├── docs/
│   └── index.html                 # GitHub Pages demo
├── requirements.txt
└── README.md
```

---

## License

MIT © 2026 PranayMahendrakar
