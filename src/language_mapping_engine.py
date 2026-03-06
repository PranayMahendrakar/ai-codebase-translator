"""
language_mapping_engine.py - Language Mapping Engine
======================================================
Maps IR nodes (language-agnostic intermediate representation)
to target-language constructs. Handles:
  - Type system mappings  (Python int -> Rust i64, Java int -> Go int)
  - Standard library equivalences
  - Idiom translations    (Python list comprehension -> Rust iterator)
  - Dependency remapping  (PyPI -> crates.io, Maven -> pkg.go.dev)
  - Architecture preservation (class hierarchy, module structure)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
from ast_generator import IRNode, IRType, NodeKind


# ---------------------------------------------------------------------------
# Type mapping tables
# ---------------------------------------------------------------------------

# Primitive type conversions between language pairs
TYPE_MAP: dict[str, dict[str, str]] = {
    # python -> rust
    "python->rust": {
        "int":       "i64",
        "float":     "f64",
        "bool":      "bool",
        "str":       "String",
        "bytes":     "Vec<u8>",
        "list":      "Vec",
        "dict":      "HashMap",
        "set":       "HashSet",
        "tuple":     "()",
        "None":      "()",
        "Optional":  "Option",
        "Any":       "Box<dyn Any>",
        "Callable":  "Box<dyn Fn>",
    },
    # python -> go
    "python->go": {
        "int":       "int64",
        "float":     "float64",
        "bool":      "bool",
        "str":       "string",
        "bytes":     "[]byte",
        "list":      "[]",
        "dict":      "map",
        "set":       "map[T]struct{}",
        "None":      "nil",
        "Optional":  "*",
        "Any":       "interface{}",
        "Callable":  "func",
    },
    # java -> go
    "java->go": {
        "int":       "int",
        "Integer":   "int",
        "long":      "int64",
        "Long":      "int64",
        "double":    "float64",
        "Double":    "float64",
        "float":     "float32",
        "boolean":   "bool",
        "Boolean":   "bool",
        "String":    "string",
        "byte[]":    "[]byte",
        "List":      "[]",
        "Map":       "map",
        "Set":       "map[T]struct{}",
        "void":      "",
        "Object":    "interface{}",
    },
    # java -> rust
    "java->rust": {
        "int":       "i32",
        "Integer":   "i32",
        "long":      "i64",
        "Long":      "i64",
        "double":    "f64",
        "Double":    "f64",
        "float":     "f32",
        "boolean":   "bool",
        "Boolean":   "bool",
        "String":    "String",
        "byte[]":    "Vec<u8>",
        "List":      "Vec",
        "Map":       "HashMap",
        "Set":       "HashSet",
        "void":      "()",
        "Object":    "Box<dyn Any>",
    },
}

# Standard library / package equivalence
STDLIB_MAP: dict[str, dict[str, str]] = {
    "python->rust": {
        "os.path":    "std::path::Path",
        "json":       "serde_json",
        "re":         "regex",
        "hashlib":    "sha2 / md5",
        "datetime":   "chrono",
        "http.client":"reqwest",
        "threading":  "std::thread",
        "asyncio":    "tokio",
        "logging":    "log / env_logger",
        "typing":     "— (native generics)",
    },
    "python->go": {
        "os":         "os",
        "os.path":    "path/filepath",
        "json":       "encoding/json",
        "re":         "regexp",
        "hashlib":    "crypto/sha256",
        "datetime":   "time",
        "http.client":"net/http",
        "threading":  "goroutines",
        "asyncio":    "goroutines + channels",
        "logging":    "log",
    },
    "java->go": {
        "java.util.ArrayList": "[]T (slice)",
        "java.util.HashMap":   "map[K]V",
        "java.util.HashSet":   "map[T]struct{}",
        "java.io":             "os / bufio",
        "java.net":            "net/http",
        "java.util.concurrent":"sync / goroutines",
        "org.slf4j":           "log",
    },
}

# Dependency/package manager remapping
DEPENDENCY_MAP: dict[str, dict[str, str]] = {
    "python->rust": {
        "requests":    "reqwest",
        "numpy":       "ndarray",
        "pandas":      "polars",
        "flask":       "actix-web / axum",
        "django":      "actix-web + diesel",
        "sqlalchemy":  "diesel",
        "pytest":      "— (cargo test)",
        "pydantic":    "serde",
        "fastapi":     "axum",
        "aiohttp":     "tokio + reqwest",
    },
    "python->go": {
        "requests":    "net/http (stdlib)",
        "flask":       "gin / echo",
        "django":      "gin + gorm",
        "sqlalchemy":  "gorm",
        "pytest":      "testing (stdlib)",
        "pydantic":    "encoding/json + validate",
        "fastapi":     "gin / fiber",
        "aiohttp":     "net/http + goroutines",
        "numpy":       "gonum",
        "pandas":      "gota/dataframe",
    },
    "java->go": {
        "spring-boot": "gin / echo",
        "hibernate":   "gorm",
        "log4j":       "zap / zerolog",
        "junit":       "testing (stdlib)",
        "jackson":     "encoding/json",
        "guava":       "— (stdlib covers most)",
        "lombok":      "— (no equivalent needed)",
    },
}


# ---------------------------------------------------------------------------
# Idiom translation rules
# ---------------------------------------------------------------------------
@dataclass
class IdiomRule:
    """A single source-to-target idiom transformation rule."""
    name: str
    description: str
    source_pattern: str          # descriptive pattern
    target_template: str         # descriptive target
    example_before: str
    example_after: str


IDIOM_RULES: dict[str, list[IdiomRule]] = {
    "python->rust": [
        IdiomRule(
            "list_comprehension",
            "Python list comprehension -> Rust iterator chain",
            "[expr for x in iterable if cond]",
            "iterable.iter().filter(|x| cond).map(|x| expr).collect::<Vec<_>>()",
            "[x * 2 for x in nums if x > 0]",
            "nums.iter().filter(|&&x| x > 0).map(|&x| x * 2).collect::<Vec<_>>()",
        ),
        IdiomRule(
            "dict_comprehension",
            "Python dict comprehension -> Rust HashMap collect",
            "{k: v for k, v in items}",
            "items.iter().map(|(k, v)| (k.clone(), v.clone())).collect::<HashMap<_,_>>()",
            "{k: v for k, v in pairs}",
            "pairs.iter().map(|(k,v)| (*k, *v)).collect::<HashMap<_,_>>()",
        ),
        IdiomRule(
            "with_statement",
            "Python context manager -> Rust RAII (automatic drop)",
            "with open(path) as f: ...",
            "let mut f = File::open(path)?; // auto-closed on drop",
            "with open('file.txt') as f:\n    data = f.read()",
            'let data = fs::read_to_string("file.txt")?;',
        ),
        IdiomRule(
            "optional_chaining",
            "Python Optional access -> Rust Option methods",
            "value.attr if value else None",
            "value.as_ref().map(|v| &v.attr)",
            "name.upper() if name else None",
            'name.as_ref().map(|n| n.to_uppercase())',
        ),
        IdiomRule(
            "exception_handling",
            "Python try/except -> Rust Result<T, E>",
            "try:\n    risky()\nexcept SomeError as e:\n    handle(e)",
            "match risky() {\n    Ok(v) => use(v),\n    Err(e) => handle(e),\n}",
            "try:\n    result = parse(text)\nexcept ValueError as e:\n    log(e)",
            'let result = parse(text).unwrap_or_else(|e| { log(e); default });',
        ),
    ],
    "python->go": [
        IdiomRule(
            "list_comprehension",
            "Python list comprehension -> Go loop with append",
            "[expr for x in iterable if cond]",
            "var result []T\nfor _, x := range iterable {\n    if cond { result = append(result, expr) }\n}",
            "[x*2 for x in nums if x > 0]",
            "var result []int\nfor _, x := range nums {\n    if x > 0 { result = append(result, x*2) }\n}",
        ),
        IdiomRule(
            "exception_handling",
            "Python exception -> Go multi-return error",
            "try:\n    result = risky()\nexcept Error as e:\n    handle(e)",
            "result, err := risky()\nif err != nil {\n    handle(err)\n}",
            "try:\n    val = parse(s)\nexcept ValueError as e:\n    print(e)",
            'val, err := parse(s)\nif err != nil { fmt.Println(err) }',
        ),
        IdiomRule(
            "class_to_struct",
            "Python class -> Go struct + methods",
            "class Foo:\n    def __init__(self, x):\n        self.x = x",
            "type Foo struct { X int }\nfunc NewFoo(x int) *Foo { return &Foo{X: x} }",
            "class Point:\n    def __init__(self, x, y):\n        self.x, self.y = x, y",
            "type Point struct { X, Y float64 }\nfunc NewPoint(x, y float64) *Point { return &Point{X:x, Y:y} }",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Mapping engine
# ---------------------------------------------------------------------------
class LanguageMappingEngine:
    """
    Core engine that maps IR nodes to target-language constructs.
    Preserves architecture while adapting to idioms.
    """

    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.pair = f"{source_lang}->{target_lang}"
        self.type_map = TYPE_MAP.get(self.pair, {})
        self.stdlib_map = STDLIB_MAP.get(self.pair, {})
        self.dep_map = DEPENDENCY_MAP.get(self.pair, {})
        self.idiom_rules = IDIOM_RULES.get(self.pair, [])

    # ------------------------------------------------------------------
    def map_type(self, ir_type: Optional[IRType]) -> str:
        """Convert a source IR type to a target-language type string."""
        if ir_type is None:
            return self._default_type()
        mapped = self.type_map.get(ir_type.name, ir_type.name)
        if ir_type.type_params:
            params = ", ".join(self.map_type(p) for p in ir_type.type_params)
            if self.target_lang == "rust":
                mapped = f"{mapped}<{params}>"
            elif self.target_lang == "go":
                mapped = f"[]{params}" if mapped == "[]" else f"{mapped}[{params}]"
            else:
                mapped = f"{mapped}<{params}>"
        if ir_type.is_nullable:
            if self.target_lang == "rust":
                mapped = f"Option<{mapped}>"
            elif self.target_lang == "go":
                mapped = f"*{mapped}"
        return mapped

    def map_stdlib(self, python_module: str) -> str:
        return self.stdlib_map.get(python_module, python_module)

    def map_dependency(self, source_dep: str) -> str:
        return self.dep_map.get(source_dep, source_dep)

    def get_applicable_idioms(self, node: IRNode) -> list[IdiomRule]:
        applicable = []
        for rule in self.idiom_rules:
            if node.kind == NodeKind.LIST_COMP and "list_comp" in rule.name:
                applicable.append(rule)
            elif node.kind == NodeKind.TRY_CATCH and "exception" in rule.name:
                applicable.append(rule)
            elif node.kind == NodeKind.CLASS and "class_to_struct" in rule.name:
                applicable.append(rule)
        return applicable

    def _default_type(self) -> str:
        defaults = {"rust": "()", "go": "interface{}", "java": "Object", "python": "Any"}
        return defaults.get(self.target_lang, "unknown")

    def describe(self) -> dict:
        return {
            "pair": self.pair,
            "type_mappings": len(self.type_map),
            "stdlib_mappings": len(self.stdlib_map),
            "dependency_mappings": len(self.dep_map),
            "idiom_rules": len(self.idiom_rules),
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def create_mapping_engine(source: str, target: str) -> LanguageMappingEngine:
    return LanguageMappingEngine(source, target)
