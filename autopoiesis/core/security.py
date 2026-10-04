"""
Security & Code Sanitization Engine for Foreign Chromosomes.

Enforces zero-trust static analysis on foreign genomes before they enter the sandbox
or reach local compilers. Rejects arbitrary syscalls, network calls, filesystem access,
and Python sandbox escape vectors.
"""

from __future__ import annotations

import ast
import re
from typing import List, Optional, Set, Tuple

from autopoiesis.core.chromosome import Chromosome, SourceType


# Disallowed Python builtins, modules, and attributes
BANNED_PYTHON_MODULES: Set[str] = {
    "os", "sys", "subprocess", "socket", "urllib", "requests", "http",
    "shutil", "pathlib", "importlib", "builtins", "posix", "nt",
    "pty", "commands", "ctypes", "winreg", "msvcrt", "platform",
    "multiprocessing", "threading", "asyncio", "signal",
}

BANNED_PYTHON_CALLS: Set[str] = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "breakpoint", "globals", "locals", "vars", "dir", "help",
    "getattr", "setattr", "delattr", "hasattr", "memoryview",
}

BANNED_PYTHON_ATTRIBUTES: Set[str] = {
    "__subclasses__", "__bases__", "__class__", "__globals__",
    "__code__", "__dict__", "__builtins__", "__import__",
    "__reduce__", "__reduce_ex__", "__getstate__", "__setstate__",
}

# Disallowed C tokens & standard libraries
BANNED_C_PATTERNS: List[re.Pattern] = [
    re.compile(r"#\s*include\s*<sys/.*>"),
    re.compile(r"#\s*include\s*<unistd\.h>"),
    re.compile(r"#\s*include\s*<windows\.h>"),
    re.compile(r"#\s*include\s*<winsock.*>"),
    re.compile(r"#\s*include\s*<netinet/.*>"),
    re.compile(r"#\s*include\s*<arpa/.*>"),
    re.compile(r"#\s*include\s*<fcntl\.h>"),
    re.compile(r"\b(system|fork|execv[pe]?|popen|fopen|freopen|remove|rename)\s*\("),
    re.compile(r"\b(socket|connect|bind|listen|accept|send|recv)\s*\("),
    re.compile(r"\b(getenv|putenv|setenv)\s*\("),
]

# Disallowed Rust tokens & crates
BANNED_RUST_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bstd::(process|net|fs|os|env|io)\b"),
    re.compile(r"\b(Command|TcpStream|TcpListener|UdpSocket|File|OpenOptions)\b"),
    re.compile(r"\bextern\s+\"C\"\s*\{[^}]*\b(system|fork|exec|socket)\b"),
]


class SecurityViolationError(Exception):
    """Raised when a candidate chromosome violates static security constraints."""
    pass


class PythonASTSecurityValidator(ast.NodeVisitor):
    """Audits pure Python AST for sandbox escape, filesystem, or network activity."""

    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_mod = alias.name.split(".")[0]
            if root_mod in BANNED_PYTHON_MODULES:
                self.violations.append(f"Disallowed import of system module: '{alias.name}'")
            elif root_mod not in ("math", "typing"):
                self.violations.append(f"Non-whitelisted module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            root_mod = node.module.split(".")[0]
            if root_mod in BANNED_PYTHON_MODULES:
                self.violations.append(f"Disallowed import from system module: '{node.module}'")
            elif root_mod not in ("math", "typing", "__future__"):
                self.violations.append(f"Non-whitelisted module import: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct calls like eval(), exec(), open()
        if isinstance(node.func, ast.Name):
            if node.func.id in BANNED_PYTHON_CALLS:
                self.violations.append(f"Disallowed builtin call: '{node.func.id}()'")
        # Check attribute calls like os.system()
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in BANNED_PYTHON_CALLS:
                self.violations.append(f"Disallowed attribute call: '.{node.func.attr}()'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in BANNED_PYTHON_ATTRIBUTES:
            self.violations.append(f"Disallowed sandbox introspection attribute: '{node.attr}'")
        self.generic_visit(node)


def audit_chromosome_security(chromosome: Chromosome) -> Tuple[bool, List[str]]:
    """
    Performs static security audit on a chromosome before any compilation or sandbox execution.
    Returns (is_secure, list_of_violations).
    """
    violations: List[str] = []

    if chromosome.source_type == SourceType.PYTHON_AST:
        try:
            tree = ast.parse(chromosome.code)
            validator = PythonASTSecurityValidator()
            validator.visit(tree)
            violations.extend(validator.violations)
        except SyntaxError as e:
            violations.append(f"Syntax error in Python code: {e}")

    elif chromosome.source_type == SourceType.C_EXTENSION:
        c_code = chromosome.mutation_meta.get("c_code", "")
        for pattern in BANNED_C_PATTERNS:
            match = pattern.search(c_code)
            if match:
                violations.append(f"Disallowed C construct detected: '{match.group(0).strip()}'")

    elif chromosome.source_type == SourceType.RUST_CDYLIB:
        rust_code = chromosome.mutation_meta.get("rust_code", "")
        for pattern in BANNED_RUST_PATTERNS:
            match = pattern.search(rust_code)
            if match:
                violations.append(f"Disallowed Rust construct detected: '{match.group(0).strip()}'")

    return (len(violations) == 0, violations)
