"""
ast_generator.py - Abstract Syntax Tree Generator
==================================================
Converts parsed source files into a language-agnostic
Intermediate Representation (IR) tree that captures
structure, types, control flow, and data flow without
being tied to any source language syntax.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional
import ast as py_ast
import json


# ---------------------------------------------------------------------------
# Node kinds
# ---------------------------------------------------------------------------
class NodeKind(str, Enum):
    MODULE      = "module"
    CLASS       = "class"
    FUNCTION    = "function"
    METHOD      = "method"
    FIELD       = "field"
    VARIABLE    = "variable"
    PARAMETER   = "parameter"
    RETURN      = "return"
    CALL        = "call"
    IMPORT      = "import"
    IF          = "if"
    FOR         = "for"
    WHILE       = "while"
    ASSIGN      = "assign"
    BINARY_OP   = "binary_op"
    UNARY_OP    = "unary_op"
    LITERAL     = "literal"
    IDENTIFIER  = "identifier"
    BLOCK       = "block"
    TRY_CATCH   = "try_catch"
    DECORATOR   = "decorator"
    LAMBDA      = "lambda"
    LIST_COMP   = "list_comp"
    UNKNOWN     = "unknown"


# ---------------------------------------------------------------------------
# Type representation
# ---------------------------------------------------------------------------
@dataclass
class IRType:
    name: str                              # e.g. "int", "str", "List[int]"
    is_nullable: bool = False
    type_params: list["IRType"] = field(default_factory=list)
    original: str = ""                     # raw annotation from source

    def __str__(self):
        params = f"[{', '.join(str(t) for t in self.type_params)}]" if self.type_params else ""
        nullable = "?" if self.is_nullable else ""
        return f"{self.name}{params}{nullable}"

    # Built-in type mappings
    PRIMITIVES = {"int", "float", "bool", "str", "bytes", "None", "any"}


# ---------------------------------------------------------------------------
# IR Node
# ---------------------------------------------------------------------------
@dataclass
class IRNode:
    kind: NodeKind
    name: Optional[str] = None
    value: Any = None
    ir_type: Optional[IRType] = None
    children: list["IRNode"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    line: int = 0
    col: int = 0
    docstring: Optional[str] = None

    def add_child(self, node: "IRNode") -> "IRNode":
        self.children.append(node)
        return self

    def find(self, kind: NodeKind) -> list["IRNode"]:
        """DFS search for nodes of a given kind."""
        results = []
        if self.kind == kind:
            results.append(self)
        for child in self.children:
            results.extend(child.find(kind))
        return results

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "value": self.value,
            "type": str(self.ir_type) if self.ir_type else None,
            "line": self.line,
            "docstring": self.docstring,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


# ---------------------------------------------------------------------------
# Python AST -> IR converter
# ---------------------------------------------------------------------------
class PythonASTConverter:
    """Convert Python source code to IR using the stdlib ast module."""

    def convert(self, source: str, filename: str = "<unknown>") -> IRNode:
        try:
            tree = py_ast.parse(source, filename=filename)
        except SyntaxError as e:
            return IRNode(NodeKind.MODULE, metadata={"parse_error": str(e)})
        return self._visit_module(tree)

    def _visit_module(self, node: py_ast.Module) -> IRNode:
        ir = IRNode(NodeKind.MODULE, metadata={"body_count": len(node.body)})
        for stmt in node.body:
            child = self._visit_stmt(stmt)
            if child:
                ir.add_child(child)
        return ir

    def _visit_stmt(self, node: py_ast.stmt) -> Optional[IRNode]:
        visitors = {
            py_ast.ClassDef:    self._visit_class,
            py_ast.FunctionDef: self._visit_function,
            py_ast.AsyncFunctionDef: self._visit_function,
            py_ast.Import:      self._visit_import,
            py_ast.ImportFrom:  self._visit_import_from,
            py_ast.Assign:      self._visit_assign,
            py_ast.Return:      self._visit_return,
            py_ast.If:          self._visit_if,
            py_ast.For:         self._visit_for,
            py_ast.While:       self._visit_while,
            py_ast.Try:         self._visit_try,
        }
        visitor = visitors.get(type(node))
        if visitor:
            return visitor(node)
        return IRNode(NodeKind.UNKNOWN, line=getattr(node, "lineno", 0))

    def _visit_class(self, node: py_ast.ClassDef) -> IRNode:
        ir = IRNode(
            NodeKind.CLASS, name=node.name,
            line=node.lineno,
            docstring=py_ast.get_docstring(node),
            metadata={"bases": [self._unparse(b) for b in node.bases]},
        )
        for decorator in node.decorator_list:
            ir.add_child(IRNode(NodeKind.DECORATOR, value=self._unparse(decorator)))
        for stmt in node.body:
            child = self._visit_stmt(stmt)
            if child:
                ir.add_child(child)
        return ir

    def _visit_function(self, node) -> IRNode:
        kind = NodeKind.METHOD if isinstance(node, py_ast.AsyncFunctionDef) else NodeKind.FUNCTION
        params = []
        for arg in node.args.args:
            ann = self._get_type(arg.annotation) if arg.annotation else None
            params.append(IRNode(NodeKind.PARAMETER, name=arg.arg, ir_type=ann))
        ret_type = self._get_type(node.returns) if node.returns else None
        ir = IRNode(
            NodeKind.FUNCTION, name=node.name,
            ir_type=ret_type, line=node.lineno,
            docstring=py_ast.get_docstring(node),
            metadata={"async": isinstance(node, py_ast.AsyncFunctionDef)},
        )
        for p in params:
            ir.add_child(p)
        for stmt in node.body:
            child = self._visit_stmt(stmt)
            if child:
                ir.add_child(child)
        return ir

    def _visit_import(self, node: py_ast.Import) -> IRNode:
        return IRNode(NodeKind.IMPORT, value=[a.name for a in node.names], line=node.lineno)

    def _visit_import_from(self, node: py_ast.ImportFrom) -> IRNode:
        return IRNode(
            NodeKind.IMPORT, name=node.module,
            value=[a.name for a in node.names], line=node.lineno,
        )

    def _visit_assign(self, node: py_ast.Assign) -> IRNode:
        return IRNode(NodeKind.ASSIGN, line=node.lineno,
                      metadata={"targets": [self._unparse(t) for t in node.targets]})

    def _visit_return(self, node: py_ast.Return) -> IRNode:
        return IRNode(NodeKind.RETURN, line=node.lineno,
                      value=self._unparse(node.value) if node.value else None)

    def _visit_if(self, node: py_ast.If) -> IRNode:
        return IRNode(NodeKind.IF, line=node.lineno,
                      metadata={"test": self._unparse(node.test)})

    def _visit_for(self, node: py_ast.For) -> IRNode:
        return IRNode(NodeKind.FOR, line=node.lineno,
                      metadata={"target": self._unparse(node.target),
                                "iter": self._unparse(node.iter)})

    def _visit_while(self, node: py_ast.While) -> IRNode:
        return IRNode(NodeKind.WHILE, line=node.lineno,
                      metadata={"test": self._unparse(node.test)})

    def _visit_try(self, node: py_ast.Try) -> IRNode:
        return IRNode(NodeKind.TRY_CATCH, line=node.lineno,
                      metadata={"handlers": len(node.handlers)})

    def _get_type(self, annotation) -> Optional[IRType]:
        if annotation is None:
            return None
        raw = self._unparse(annotation)
        return IRType(name=raw, original=raw)

    @staticmethod
    def _unparse(node) -> str:
        if node is None:
            return ""
        try:
            return py_ast.unparse(node)
        except Exception:
            return str(node)


# ---------------------------------------------------------------------------
# Stub converters for other languages
# (Full implementations use tree-sitter or ANTLR in production)
# ---------------------------------------------------------------------------
class JavaASTConverter:
    """Stub: converts Java source to IR via regex heuristics."""
    def convert(self, source: str, filename: str = "<unknown>") -> IRNode:
        import re
        root = IRNode(NodeKind.MODULE, metadata={"language": "java"})
        for m in re.finditer(r"public\s+class\s+(\w+)", source):
            cls = IRNode(NodeKind.CLASS, name=m.group(1))
            for fm in re.finditer(r"public\s+\w+\s+(\w+)\s*\(", source):
                cls.add_child(IRNode(NodeKind.FUNCTION, name=fm.group(1)))
            root.add_child(cls)
        return root


class GoASTConverter:
    """Stub: converts Go source to IR via regex heuristics."""
    def convert(self, source: str, filename: str = "<unknown>") -> IRNode:
        import re
        root = IRNode(NodeKind.MODULE, metadata={"language": "go"})
        for m in re.finditer(r"^func\s+(\w+)\s*\(", source, re.MULTILINE):
            root.add_child(IRNode(NodeKind.FUNCTION, name=m.group(1)))
        for m in re.finditer(r"^type\s+(\w+)\s+struct", source, re.MULTILINE):
            root.add_child(IRNode(NodeKind.CLASS, name=m.group(1)))
        return root


class RustASTConverter:
    """Stub: converts Rust source to IR via regex heuristics."""
    def convert(self, source: str, filename: str = "<unknown>") -> IRNode:
        import re
        root = IRNode(NodeKind.MODULE, metadata={"language": "rust"})
        for m in re.finditer(r"pub\s+fn\s+(\w+)", source):
            root.add_child(IRNode(NodeKind.FUNCTION, name=m.group(1)))
        for m in re.finditer(r"pub\s+struct\s+(\w+)", source):
            root.add_child(IRNode(NodeKind.CLASS, name=m.group(1)))
        return root


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
CONVERTERS = {
    "python": PythonASTConverter,
    "java":   JavaASTConverter,
    "go":     GoASTConverter,
    "rust":   RustASTConverter,
}


def generate_ast(source: str, language: str) -> dict:
    """Public API: returns the IR tree as a serialisable dict."""
    converter_cls = CONVERTERS.get(language)
    if not converter_cls:
        return IRNode(NodeKind.MODULE,
                      metadata={"error": f"No converter for {language}"}).to_dict()
    return converter_cls().convert(source).to_dict()
