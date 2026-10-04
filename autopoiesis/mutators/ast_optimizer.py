"""
Pure Python AST Optimizer Mutator.

Applies algorithmic AST transformations:
- Local variable caching of global and builtin lookups
- Constant folding of mathematical expressions
- Augmented assignment transformations
"""

from __future__ import annotations

import ast
import inspect
from typing import Any, List, Optional, Set

from autopoiesis.core.chromosome import Chromosome, SourceType
from autopoiesis.core.hotspot import BottleneckProfile
from autopoiesis.mutators.base import BaseMutator


class ConstantFoldingTransformer(ast.NodeTransformer):
    """Folds arithmetic operations on literals into computed constants."""

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        self.generic_visit(node)
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            lv = node.left.value
            rv = node.right.value
            try:
                val = None
                if isinstance(node.op, ast.Add):
                    val = lv + rv
                elif isinstance(node.op, ast.Sub):
                    val = lv - rv
                elif isinstance(node.op, ast.Mult):
                    val = lv * rv
                elif isinstance(node.op, ast.Div) and rv != 0:
                    val = lv / rv
                elif isinstance(node.op, ast.FloorDiv) and rv != 0:
                    val = lv // rv
                elif isinstance(node.op, ast.Mod) and rv != 0:
                    val = lv % rv
                elif isinstance(node.op, ast.Pow) and abs(rv) <= 10:
                    val = lv ** rv

                if val is not None and isinstance(val, (int, float)):
                    return ast.copy_location(ast.Constant(value=val), node)
            except Exception:
                pass
        return node


class GlobalLookupOptimizer(ast.NodeTransformer):
    """Caches frequently accessed builtins and globals into fast local variables."""

    CACHABLE_BUILTINS = {
        "range", "len", "abs", "min", "max", "sum", "int", "float", "round",
        "enumerate", "zip", "math"
    }

    def __init__(self, target_func_name: str) -> None:
        self.target_func_name = target_func_name
        self.used_builtins: Set[str] = set()
        self.in_loop = False

    def visit_For(self, node: ast.For) -> Any:
        prev = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = prev
        return node

    def visit_While(self, node: ast.While) -> Any:
        prev = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = prev
        return node

    def visit_Name(self, node: ast.Name) -> Any:
        if self.in_loop and isinstance(node.ctx, ast.Load):
            if node.id in self.CACHABLE_BUILTINS:
                self.used_builtins.add(node.id)
                # Rewrite lookup to local cached alias
                return ast.copy_location(ast.Name(id=f"_fast_{node.id}", ctx=ast.Load()), node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.name != self.target_func_name:
            return node

        # First pass: find and rename builtins inside loops
        self.generic_visit(node)

        # Inject local caching assignments at the top of the function
        # e.g.: _fast_range = range
        if self.used_builtins:
            injected_assigns = []
            for b in sorted(self.used_builtins):
                assign_node = ast.Assign(
                    targets=[ast.Name(id=f"_fast_{b}", ctx=ast.Store())],
                    value=ast.Name(id=b, ctx=ast.Load()),
                )
                ast.copy_location(assign_node, node)
                injected_assigns.append(assign_node)

            # Preserve docstring if present as first statement
            insert_idx = 0
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                insert_idx = 1
            node.body = node.body[:insert_idx] + injected_assigns + node.body[insert_idx:]

        return node


class ASTOptimizerMutator(BaseMutator):
    """Mutator performing sound AST optimizations on Python code."""

    @property
    def name(self) -> str:
        return "ast_optimizer"

    @property
    def target_source_type(self) -> SourceType:
        return SourceType.PYTHON_AST

    def can_mutate(self, bottleneck: BottleneckProfile) -> bool:
        return True  # Can attempt Python AST optimization on any target

    def mutate(
        self,
        parent_chromosome: Chromosome,
        bottleneck: BottleneckProfile,
        target_dir: Optional[str] = None,
        generation: Optional[int] = None,
        parent_id: Optional[str] = None,
    ) -> Optional[Chromosome]:
        try:
            tree = ast.parse(parent_chromosome.code)
            target_symbol = parent_chromosome.entry_symbol

            # 1. Constant folding
            folder = ConstantFoldingTransformer()
            tree = folder.visit(tree)

            # 2. Global lookup local caching
            lookup_opt = GlobalLookupOptimizer(target_func_name=target_symbol)
            tree = lookup_opt.visit(tree)

            # 3. Ensure standard imports (e.g. math) exist if referenced
            has_math_ref = any(
                isinstance(n, ast.Name) and n.id == "math"
                for n in ast.walk(tree)
            )
            has_math_import = any(
                (isinstance(n, ast.Import) and any(alias.name == "math" for alias in n.names)) or
                (isinstance(n, ast.ImportFrom) and n.module == "math")
                for n in ast.walk(tree)
            )
            if has_math_ref and not has_math_import:
                tree.body.insert(0, ast.Import(names=[ast.alias(name="math", asname=None)]))

            ast.fix_missing_locations(tree)
            optimized_code = ast.unparse(tree)

            gen = generation if generation is not None else parent_chromosome.generation + 1
            p_id = parent_id if parent_id is not None else parent_chromosome.id

            return Chromosome.create(
                generation=gen,
                source_type=SourceType.PYTHON_AST,
                entry_symbol=target_symbol,
                code=optimized_code,
                parent_id=p_id,
                mutation_meta={
                    "mutator": self.name,
                    "cached_builtins": list(lookup_opt.used_builtins),
                },
            )
        except Exception:
            return None
