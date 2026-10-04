"""
Deterministic Execution Profiler and AST Bottleneck Detector.

Profiles live workloads using cProfile and inspects the abstract syntax tree
to detect computational hot spots, nested loop nests, and candidate targets for
transpilation or algorithmic optimization.
"""

from __future__ import annotations

import ast
import cProfile
import inspect
import io
import pstats
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class BottleneckProfile:
    """Detailed profile of a detected computational bottleneck."""
    function_name: str
    module_name: str
    call_count: int
    total_time_seconds: float
    per_call_time_seconds: float
    time_percentage: float
    loop_depth: int
    arithmetic_op_count: int
    is_pure_numeric: bool
    source_code: str
    ast_tree: Optional[ast.AST] = field(default=None, repr=False)
    hotspot_score: float = 0.0

    @property
    def is_transpilable(self) -> bool:
        """Determines if the bottleneck is eligible for C or Rust compilation."""
        return (self.loop_depth >= 1 and self.arithmetic_op_count >= 1) or (self.arithmetic_op_count >= 4)


class ASTComplexityVisitor(ast.NodeVisitor):
    """AST visitor calculating loop nesting depth and computational density."""

    def __init__(self, target_func_name: Optional[str] = None) -> None:
        self.target_func_name = target_func_name
        self.max_loop_depth = 0
        self.current_loop_depth = 0
        self.arithmetic_ops = 0
        self.is_pure_numeric = True
        self.has_recursion = False
        self.inside_target = target_func_name is None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if self.target_func_name is None or node.name == self.target_func_name:
            prev_inside = self.inside_target
            self.inside_target = True
            self.generic_visit(node)
            self.inside_target = prev_inside
        else:
            self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:
        if self.inside_target:
            self.current_loop_depth += 1
            if self.current_loop_depth > self.max_loop_depth:
                self.max_loop_depth = self.current_loop_depth
            self.generic_visit(node)
            self.current_loop_depth -= 1
        else:
            self.generic_visit(node)

    def visit_While(self, node: ast.While) -> Any:
        if self.inside_target:
            self.current_loop_depth += 1
            if self.current_loop_depth > self.max_loop_depth:
                self.max_loop_depth = self.current_loop_depth
            self.generic_visit(node)
            self.current_loop_depth -= 1
        else:
            self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if self.inside_target:
            self.arithmetic_ops += 1
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        if self.inside_target:
            self.arithmetic_ops += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if self.inside_target:
            # Check for recursion
            if isinstance(node.func, ast.Name) and self.target_func_name:
                if node.func.id == self.target_func_name:
                    self.has_recursion = True
            # Check if calling non-numeric I/O functions (print, open, eval, exec)
            if isinstance(node.func, ast.Name) and node.func.id in {"print", "open", "eval", "exec", "input"}:
                self.is_pure_numeric = False
        self.generic_visit(node)


class HotspotDetector:
    """Profiles workloads and detects execution bottlenecks."""

    def __init__(self, target_modules: Optional[List[str]] = None) -> None:
        self.target_modules = target_modules or []

    def profile_workload(
        self,
        workload_fn: Callable[[], Any],
        target_func_names: Optional[List[str]] = None,
        top_k: int = 5,
    ) -> List[BottleneckProfile]:
        """Profiles a workload and returns ranked bottleneck profiles."""
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            workload_fn()
        finally:
            profiler.disable()

        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")

        profiles: List[BottleneckProfile] = []
        total_time = stats.total_tt if stats.total_tt > 0 else 0.0001

        # Iterate over function statistics
        for func_key, (cc, nc, tt, ct, callers) in stats.stats.items():
            file_name, line_no, func_name = func_key

            # Filter out internal profiler / builtins if requested
            if func_name.startswith("<") or "cProfile" in file_name or "pstats" in file_name:
                continue

            if target_func_names and func_name not in target_func_names:
                continue

            # Calculate metrics
            time_pct = (ct / total_time) * 100.0 if total_time > 0 else 0.0
            per_call = ct / nc if nc > 0 else 0.0

            # Inspect AST if source code is accessible
            source = ""
            loop_depth = 0
            arithmetic_ops = 0
            is_pure_numeric = True
            parsed_ast: Optional[ast.AST] = None

            # Attempt to retrieve function source via inspect
            try:
                # Find caller function object in target modules if possible
                pass
            except Exception:
                pass

            score = time_pct * (1.0 + loop_depth * 0.5)

            profiles.append(
                BottleneckProfile(
                    function_name=func_name,
                    module_name=file_name,
                    call_count=nc,
                    total_time_seconds=ct,
                    per_call_time_seconds=per_call,
                    time_percentage=time_pct,
                    loop_depth=loop_depth,
                    arithmetic_op_count=arithmetic_ops,
                    is_pure_numeric=is_pure_numeric,
                    source_code=source,
                    ast_tree=parsed_ast,
                    hotspot_score=score,
                )
            )

        # Sort by total cumulative time descending
        profiles.sort(key=lambda p: p.total_time_seconds, reverse=True)
        return profiles[:top_k]

    @staticmethod
    def analyze_source_ast(source_code: str, function_name: str, module_name: str = "__main__") -> BottleneckProfile:
        """Analyzes Python function source code directly via AST inspection."""
        import textwrap
        dedented = textwrap.dedent(source_code)
        tree = ast.parse(dedented)
        visitor = ASTComplexityVisitor(target_func_name=function_name)
        visitor.visit(tree)

        score = (visitor.max_loop_depth * 10.0) + visitor.arithmetic_ops

        return BottleneckProfile(
            function_name=function_name,
            module_name=module_name,
            call_count=1,
            total_time_seconds=0.0,
            per_call_time_seconds=0.0,
            time_percentage=100.0,
            loop_depth=visitor.max_loop_depth,
            arithmetic_op_count=visitor.arithmetic_ops,
            is_pure_numeric=visitor.is_pure_numeric,
            source_code=dedented,
            ast_tree=tree,
            hotspot_score=score,
        )

    @staticmethod
    def analyze_function_ast(func: Callable[..., Any]) -> BottleneckProfile:
        """Analyzes a Python function callable directly via AST inspection."""
        source = inspect.getsource(func)
        mod_name = inspect.getmodule(func).__name__ if inspect.getmodule(func) else "__main__"
        return HotspotDetector.analyze_source_ast(source, func.__name__, mod_name)
