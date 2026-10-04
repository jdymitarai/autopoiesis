"""
Autonomous Python-to-C Transpiler and Dynamic Shared Library Compiler.

Autonomously extracts Python computational bottlenecks, transpiles numeric AST
structures into optimized ISO C99, compiles via gcc/clang with aggressive optimizations
(-O3 -ffast-math -shared -fPIC), and synthesizes a high-performance ctypes bridge.
"""

from __future__ import annotations

import ast
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

from autopoiesis.core.chromosome import Chromosome, SourceType
from autopoiesis.core.hotspot import BottleneckProfile
from autopoiesis.mutators.base import BaseMutator


class ASTToCTranspiler(ast.NodeVisitor):
    """Transpiles Python numeric AST into high-performance C99 code."""

    def __init__(self, target_func_name: str) -> None:
        self.target_func_name = target_func_name
        self.c_lines: List[str] = []
        self.indent_level = 0
        self.declared_vars: Dict[str, str] = {}  # var_name -> c_type
        self.func_args: List[Tuple[str, str]] = []  # (name, c_type)
        self.return_type = "double"
        self.headers: Set[str] = {"<stdio.h>", "<stdlib.h>", "<stdint.h>", "<stdbool.h>", "<math.h>"}
        self.inside_target = False

    def indent(self) -> str:
        return "    " * self.indent_level

    def emit(self, line: str) -> None:
        self.c_lines.append(f"{self.indent()}{line}")

    def transpile(self, tree: ast.AST) -> Tuple[str, List[Tuple[str, str]], str]:
        """Returns (c_source_code, argument_specs, return_type)."""
        self.visit(tree)
        header_lines = [f"#include {h}" for h in sorted(self.headers)]
        export_macro = [
            "",
            "#if defined(_WIN32) || defined(__CYGWIN__)",
            "  #define EXPORT __declspec(dllexport)",
            "#else",
            "  #define EXPORT __attribute__((visibility(\"default\")))",
            "#endif",
            "",
        ]
        full_code = "\n".join(header_lines + export_macro + self.c_lines)
        return full_code, self.func_args, self.return_type

    def _infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, int):
                return "int64_t"
            if isinstance(node.value, float):
                return "double"
        elif isinstance(node, ast.BinOp):
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if "double" in (lt, rt) or isinstance(node.op, ast.Div):
                return "double"
            return "int64_t"
        elif isinstance(node, ast.Name):
            if node.id in self.declared_vars:
                return self.declared_vars[node.id]
            for arg_name, arg_type in self.func_args:
                if arg_name == node.id:
                    return arg_type
        return "double"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.name != self.target_func_name:
            return

        self.inside_target = True

        # Inspect argument types from annotations or defaults
        self.func_args = []
        for arg in node.args.args:
            arg_name = arg.arg
            c_type = "double"
            if arg.annotation:
                ann_str = ast.unparse(arg.annotation).lower()
                if "int" in ann_str:
                    c_type = "int64_t"
                elif "float" in ann_str:
                    c_type = "double"
                elif "bool" in ann_str:
                    c_type = "bool"
            else:
                if "iter" in arg_name or "count" in arg_name or "len" in arg_name or "n" == arg_name or "idx" in arg_name or "steps" in arg_name:
                    c_type = "int64_t"
                else:
                    c_type = "double"

            self.func_args.append((arg_name, c_type))
            self.declared_vars[arg_name] = c_type

        # Scan body for returns to infer return type
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                self.return_type = self._infer_type(child.value)
                break

        arg_sig = ", ".join(f"{t} {name}" for name, t in self.func_args)
        if not arg_sig:
            arg_sig = "void"

        self.emit(f"EXPORT {self.return_type} {node.name}({arg_sig}) {{")
        self.indent_level += 1

        for stmt in node.body:
            self.visit(stmt)

        self.indent_level -= 1
        self.emit("}")
        self.inside_target = False

    def visit_Assign(self, node: ast.Assign) -> Any:
        if not self.inside_target:
            return

        rhs_expr = self._transpile_expr(node.value)
        rhs_type = self._infer_type(node.value)

        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if var_name not in self.declared_vars:
                    self.declared_vars[var_name] = rhs_type
                    self.emit(f"{rhs_type} {var_name} = {rhs_expr};")
                else:
                    self.emit(f"{var_name} = {rhs_expr};")
            elif isinstance(target, ast.Subscript):
                target_expr = self._transpile_expr(target)
                self.emit(f"{target_expr} = {rhs_expr};")

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        if not self.inside_target:
            return

        target_str = self._transpile_expr(node.target)
        val_str = self._transpile_expr(node.value)
        op_str = self._get_op_str(node.op)
        self.emit(f"{target_str} {op_str}= {val_str};")

    def visit_For(self, node: ast.For) -> Any:
        if not self.inside_target:
            return

        # Handle range() loops
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            args = node.iter.args
            var_name = node.target.id if isinstance(node.target, ast.Name) else "_i"
            self.declared_vars[var_name] = "int64_t"

            if len(args) == 1:
                start = "0"
                stop = self._transpile_expr(args[0])
                step = "1"
            elif len(args) == 2:
                start = self._transpile_expr(args[0])
                stop = self._transpile_expr(args[1])
                step = "1"
            elif len(args) >= 3:
                start = self._transpile_expr(args[0])
                stop = self._transpile_expr(args[1])
                step = self._transpile_expr(args[2])
            else:
                start, stop, step = "0", "0", "1"

            if step == "1":
                self.emit(f"for (int64_t {var_name} = {start}; {var_name} < {stop}; {var_name}++) {{")
            else:
                self.emit(f"for (int64_t {var_name} = {start}; {var_name} < {stop}; {var_name} += {step}) {{")

            self.indent_level += 1
            for stmt in node.body:
                self.visit(stmt)
            self.indent_level -= 1
            self.emit("}")
        else:
            # Generic loop
            self.emit("/* Unsupported iterable loop in C transpiler */")

    def visit_While(self, node: ast.While) -> Any:
        if not self.inside_target:
            return
        cond = self._transpile_expr(node.test)
        self.emit(f"while ({cond}) {{")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        self.emit("}")

    def visit_If(self, node: ast.If) -> Any:
        if not self.inside_target:
            return
        cond = self._transpile_expr(node.test)
        self.emit(f"if ({cond}) {{")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1

        if node.orelse:
            self.emit("} else {")
            self.indent_level += 1
            for stmt in node.orelse:
                self.visit(stmt)
            self.indent_level -= 1
        self.emit("}")

    def visit_Return(self, node: ast.Return) -> Any:
        if not self.inside_target:
            return
        if node.value:
            val = self._transpile_expr(node.value)
            self.emit(f"return ({self.return_type})({val});")
        else:
            self.emit("return;")

    def _transpile_expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if isinstance(node.value, float):
                # Ensure float literal representation
                s = repr(node.value)
                return s if "." in s or "e" in s or "E" in s else f"{s}.0"
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.UnaryOp):
            op = "-" if isinstance(node.op, ast.USub) else "!" if isinstance(node.op, ast.Not) else "+"
            return f"({op}{self._transpile_expr(node.operand)})"
        elif isinstance(node, ast.BinOp):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            if isinstance(node.op, ast.Pow):
                return f"pow({left}, {right})"
            op_str = self._get_op_str(node.op)
            return f"({left} {op_str} {right})"
        elif isinstance(node, ast.Compare):
            left = self._transpile_expr(node.left)
            comps = []
            for op, comp in zip(node.ops, node.comparators):
                op_str = self._get_cmp_op(op)
                right = self._transpile_expr(comp)
                comps.append(f"{left} {op_str} {right}")
                left = right
            return " && ".join(comps)
        elif isinstance(node, ast.Call):
            func_name = ast.unparse(node.func)
            args = [self._transpile_expr(a) for a in node.args]
            if func_name == "float":
                return f"((double)({args[0]}))"
            elif func_name == "int":
                return f"((int64_t)({args[0]}))"
            elif func_name == "abs":
                return f"fabs({args[0]})"
            elif func_name in ("math.sqrt", "sqrt"):
                return f"sqrt({args[0]})"
            elif func_name in ("math.sin", "sin"):
                return f"sin({args[0]})"
            elif func_name in ("math.cos", "cos"):
                return f"cos({args[0]})"
            elif func_name in ("math.pow", "pow"):
                return f"pow({args[0]}, {args[1]})"
            return f"{func_name}({', '.join(args)})"
        return "0"

    def _get_op_str(self, op: ast.operator) -> str:
        if isinstance(op, ast.Add): return "+"
        if isinstance(op, ast.Sub): return "-"
        if isinstance(op, ast.Mult): return "*"
        if isinstance(op, ast.Div): return "/"
        if isinstance(op, ast.Mod): return "%"
        return "+"

    def _get_cmp_op(self, op: ast.cmpop) -> str:
        if isinstance(op, ast.Eq): return "=="
        if isinstance(op, ast.NotEq): return "!="
        if isinstance(op, ast.Lt): return "<"
        if isinstance(op, ast.LtE): return "<="
        if isinstance(op, ast.Gt): return ">"
        if isinstance(op, ast.GtE): return ">="
        return "=="


class CSynthesizerMutator(BaseMutator):
    """Mutator that transpiles Python AST bottlenecks into C99 shared libraries."""

    def __init__(self, compiler: Optional[str] = None, extra_flags: Optional[List[str]] = None) -> None:
        self.compiler = compiler or self._detect_c_compiler()
        self.extra_flags = extra_flags or ["-O3", "-fPIC", "-shared", "-ffast-math"]

    @property
    def name(self) -> str:
        return "c_synthesizer"

    @property
    def target_source_type(self) -> SourceType:
        return SourceType.C_EXTENSION

    def _detect_c_compiler(self) -> Optional[str]:
        for c in ["gcc", "clang"]:
            found = shutil.which(c)
            if found:
                return found
        return None

    def can_mutate(self, bottleneck: BottleneckProfile) -> bool:
        if not self.compiler:
            return False
        return bottleneck.is_transpilable

    def mutate(
        self,
        parent_chromosome: Chromosome,
        bottleneck: BottleneckProfile,
        target_dir: Optional[str] = None,
    ) -> Optional[Chromosome]:
        if not self.compiler:
            return None

        out_dir = target_dir or os.path.join(os.getcwd(), ".autopoiesis_artifacts")
        os.makedirs(out_dir, exist_ok=True)

        try:
            tree = ast.parse(parent_chromosome.code)
            target_symbol = parent_chromosome.entry_symbol

            transpiler = ASTToCTranspiler(target_func_name=target_symbol)
            c_code, arg_specs, return_type = transpiler.transpile(tree)

            # Generate C source file
            gen = parent_chromosome.generation + 1
            c_filename = f"{target_symbol}_gen{gen}_{parent_chromosome.id[:6]}.c"
            c_path = os.path.join(out_dir, c_filename)

            with open(c_path, "w", encoding="utf-8") as f:
                f.write(c_code)

            # Determine dynamic library extension
            is_windows = platform.system() == "Windows"
            ext = ".dll" if is_windows else ".so"
            lib_filename = f"lib{target_symbol}_gen{gen}_{parent_chromosome.id[:6]}{ext}"
            lib_path = os.path.join(out_dir, lib_filename)

            # Compile invocation
            compile_cmd = [self.compiler] + self.extra_flags + [c_path, "-o", lib_path]
            if not is_windows:
                compile_cmd.append("-lm")

            res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                return None

            # Generate ctypes bridge wrapper
            wrapper_code = self._generate_ctypes_wrapper(
                target_symbol=target_symbol,
                arg_specs=arg_specs,
                return_type=return_type,
            )

            return Chromosome.create(
                generation=gen,
                source_type=SourceType.C_EXTENSION,
                entry_symbol=target_symbol,
                code=wrapper_code,
                parent_id=parent_chromosome.id,
                compiled_artifact_path=lib_path,
                compiler_flags=self.extra_flags,
                mutation_meta={
                    "mutator": self.name,
                    "c_source_path": c_path,
                    "c_code": c_code,
                    "compiler": self.compiler,
                    "arg_specs": arg_specs,
                    "return_type": return_type,
                },
            )
        except Exception:
            return None

    def _generate_ctypes_wrapper(
        self,
        target_symbol: str,
        arg_specs: List[Tuple[str, str]],
        return_type: str,
    ) -> str:
        """Synthesizes the Python ctypes binding code."""
        c_to_ctypes = {
            "double": "ctypes.c_double",
            "int64_t": "ctypes.c_longlong",
            "bool": "ctypes.c_bool",
            "void": "None",
        }

        arg_types = ", ".join(c_to_ctypes.get(t, "ctypes.c_double") for _, t in arg_specs)
        res_type = c_to_ctypes.get(return_type, "ctypes.c_double")

        param_names = [name for name, _ in arg_specs]
        param_sig = ", ".join(param_names)

        # Type conversion calls
        conversions = []
        for name, t in arg_specs:
            ctype_cls = c_to_ctypes.get(t, "ctypes.c_double")
            conversions.append(f"{ctype_cls}({name})")
        conv_args = ", ".join(conversions)

        lines = [
            "import ctypes",
            "",
            f"_c_func = lib.{target_symbol}",
            f"_c_func.argtypes = [{arg_types}]",
            f"_c_func.restype = {res_type}",
            "",
            f"def {target_symbol}({param_sig}):",
            f"    return _c_func({conv_args})",
        ]
        return "\n".join(lines)
