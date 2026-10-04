"""
Autonomous Python-to-Rust Transpiler and Dynamic cdylib Compiler.

Transpiles Python numeric/algorithmic bottlenecks into memory-safe, ultra-high-speed
Rust with C ABI linkage (#[no_mangle] pub extern "C" fn), compiles via rustc
with opt-level=3, and synthesizes the ctypes adapter bridge.
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


class ASTToRustTranspiler(ast.NodeVisitor):
    """Transpiles Python numeric AST into Rust with C ABI export."""

    def __init__(self, target_func_name: str) -> None:
        self.target_func_name = target_func_name
        self.rust_lines: List[str] = []
        self.indent_level = 0
        self.declared_vars: Dict[str, str] = {}  # var_name -> rust_type
        self.func_args: List[Tuple[str, str]] = []  # (name, rust_type)
        self.return_type = "f64"
        self.inside_target = False

    def indent(self) -> str:
        return "    " * self.indent_level

    def emit(self, line: str) -> None:
        self.rust_lines.append(f"{self.indent()}{line}")

    def transpile(self, tree: ast.AST) -> Tuple[str, List[Tuple[str, str]], str]:
        self.visit(tree)
        header = [
            "// Auto-synthesized by Autopoiesis Engine",
            "#![allow(unused_variables, unused_mut, non_snake_case)]",
            "",
        ]
        full_code = "\n".join(header + self.rust_lines)
        return full_code, self.func_args, self.return_type

    def _infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, int):
                return "i64"
            if isinstance(node.value, float):
                return "f64"
        elif isinstance(node, ast.BinOp):
            lt = self._infer_type(node.left)
            rt = self._infer_type(node.right)
            if "f64" in (lt, rt) or isinstance(node.op, ast.Div):
                return "f64"
            return "i64"
        elif isinstance(node, ast.Name):
            if node.id in self.declared_vars:
                return self.declared_vars[node.id]
            for arg_name, arg_type in self.func_args:
                if arg_name == node.id:
                    return arg_type
        return "f64"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        if node.name != self.target_func_name:
            return

        self.inside_target = True

        self.func_args = []
        for arg in node.args.args:
            arg_name = arg.arg
            r_type = "f64"
            if arg.annotation:
                ann = ast.unparse(arg.annotation).lower()
                if "int" in ann:
                    r_type = "i64"
                elif "float" in ann:
                    r_type = "f64"
                elif "bool" in ann:
                    r_type = "bool"
            else:
                if "iter" in arg_name or "count" in arg_name or "len" in arg_name or "n" == arg_name or "idx" in arg_name:
                    r_type = "i64"
                else:
                    r_type = "f64"

            self.func_args.append((arg_name, r_type))
            self.declared_vars[arg_name] = r_type

        # Scan for returns
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                self.return_type = self._infer_type(child.value)
                break

        arg_sig = ", ".join(f"mut {name}: {t}" for name, t in self.func_args)

        self.emit("#[no_mangle]")
        self.emit(f"pub extern \"C\" fn {node.name}({arg_sig}) -> {self.return_type} {{")
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
                    self.emit(f"let mut {var_name}: {rhs_type} = {rhs_expr};")
                else:
                    self.emit(f"{var_name} = {rhs_expr};")

    def visit_AugAssign(self, node: ast.AugAssign) -> Any:
        if not self.inside_target:
            return

        target_str = self._transpile_expr(node.target)
        val_str = self._transpile_expr(node.value)
        op_str = "+" if isinstance(node.op, ast.Add) else "-" if isinstance(node.op, ast.Sub) else "*" if isinstance(node.op, ast.Mult) else "/"
        self.emit(f"{target_str} {op_str}= {val_str};")

    def visit_For(self, node: ast.For) -> Any:
        if not self.inside_target:
            return

        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            args = node.iter.args
            var_name = node.target.id if isinstance(node.target, ast.Name) else "_i"
            self.declared_vars[var_name] = "i64"

            if len(args) == 1:
                start = "0"
                stop = self._transpile_expr(args[0])
            elif len(args) >= 2:
                start = self._transpile_expr(args[0])
                stop = self._transpile_expr(args[1])
            else:
                start, stop = "0", "0"

            self.emit(f"for {var_name} in ({start} as i64)..({stop} as i64) {{")
            self.indent_level += 1
            for stmt in node.body:
                self.visit(stmt)
            self.indent_level -= 1
            self.emit("}")

    def visit_While(self, node: ast.While) -> Any:
        if not self.inside_target:
            return
        cond = self._transpile_expr(node.test)
        self.emit(f"while {cond} {{")
        self.indent_level += 1
        for stmt in node.body:
            self.visit(stmt)
        self.indent_level -= 1
        self.emit("}")

    def visit_If(self, node: ast.If) -> Any:
        if not self.inside_target:
            return
        cond = self._transpile_expr(node.test)
        self.emit(f"if {cond} {{")
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
            self.emit(f"return ({val}) as {self.return_type};")
        else:
            self.emit("return;")

    def _transpile_expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if isinstance(node.value, float):
                s = repr(node.value)
                return f"{s}_f64" if ("." in s or "e" in s or "E" in s) else f"{s}.0_f64"
            if isinstance(node.value, int):
                return f"{node.value}_i64"
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.UnaryOp):
            op = "-" if isinstance(node.op, ast.USub) else "!" if isinstance(node.op, ast.Not) else "+"
            return f"({op}{self._transpile_expr(node.operand)})"
        elif isinstance(node, ast.BinOp):
            left = self._transpile_expr(node.left)
            right = self._transpile_expr(node.right)
            if isinstance(node.op, ast.Add): return f"({left} + {right})"
            if isinstance(node.op, ast.Sub): return f"({left} - {right})"
            if isinstance(node.op, ast.Mult): return f"({left} * {right})"
            if isinstance(node.op, ast.Div): return f"({left} / {right})"
            if isinstance(node.op, ast.Mod): return f"({left} % {right})"
            if isinstance(node.op, ast.Pow): return f"({left}).powf({right})"
            return f"({left} + {right})"
        elif isinstance(node, ast.Compare):
            left = self._transpile_expr(node.left)
            comps = []
            for op, comp in zip(node.ops, node.comparators):
                op_str = "==" if isinstance(op, ast.Eq) else "!=" if isinstance(op, ast.NotEq) else "<" if isinstance(op, ast.Lt) else "<=" if isinstance(op, ast.LtE) else ">" if isinstance(op, ast.Gt) else ">="
                right = self._transpile_expr(comp)
                comps.append(f"{left} {op_str} {right}")
                left = right
            return " && ".join(comps)
        elif isinstance(node, ast.Call):
            func_name = ast.unparse(node.func)
            args = [self._transpile_expr(a) for a in node.args]
            if func_name == "float":
                return f"({args[0]} as f64)"
            elif func_name == "int":
                return f"({args[0]} as i64)"
            elif func_name == "abs":
                return f"({args[0]}).abs()"
            elif func_name in ("math.sqrt", "sqrt"):
                return f"({args[0]}).sqrt()"
            elif func_name in ("math.sin", "sin"):
                return f"({args[0]}).sin()"
            elif func_name in ("math.cos", "cos"):
                return f"({args[0]}).cos()"
            return f"{func_name}({', '.join(args)})"
        return "0.0"


class RustSynthesizerMutator(BaseMutator):
    """Mutator transpiling Python bottlenecks into compiled Rust cdylib libraries."""

    def __init__(self, rustc_path: Optional[str] = None) -> None:
        self.rustc_path = rustc_path or shutil.which("rustc")

    @property
    def name(self) -> str:
        return "rust_synthesizer"

    @property
    def target_source_type(self) -> SourceType:
        return SourceType.RUST_CDYLIB

    def can_mutate(self, bottleneck: BottleneckProfile) -> bool:
        if not self.rustc_path:
            return False
        return bottleneck.is_transpilable

    def mutate(
        self,
        parent_chromosome: Chromosome,
        bottleneck: BottleneckProfile,
        target_dir: Optional[str] = None,
    ) -> Optional[Chromosome]:
        if not self.rustc_path:
            return None

        out_dir = target_dir or os.path.join(os.getcwd(), ".autopoiesis_artifacts")
        os.makedirs(out_dir, exist_ok=True)

        try:
            tree = ast.parse(parent_chromosome.code)
            target_symbol = parent_chromosome.entry_symbol

            transpiler = ASTToRustTranspiler(target_func_name=target_symbol)
            rust_code, arg_specs, return_type = transpiler.transpile(tree)

            gen = parent_chromosome.generation + 1
            rs_filename = f"{target_symbol}_gen{gen}_{parent_chromosome.id[:6]}.rs"
            rs_path = os.path.join(out_dir, rs_filename)

            with open(rs_path, "w", encoding="utf-8") as f:
                f.write(rust_code)

            is_windows = platform.system() == "Windows"
            ext = ".dll" if is_windows else ".so"
            lib_filename = f"librust_{target_symbol}_gen{gen}_{parent_chromosome.id[:6]}{ext}"
            lib_path = os.path.join(out_dir, lib_filename)

            # Compile invocation: rustc --crate-type cdylib -C opt-level=3
            compile_cmd = [
                self.rustc_path,
                "--crate-type",
                "cdylib",
                "-C",
                "opt-level=3",
                rs_path,
                "-o",
                lib_path,
            ]

            res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=20)
            if res.returncode != 0:
                return None

            wrapper_code = self._generate_ctypes_wrapper(target_symbol, arg_specs, return_type)

            return Chromosome.create(
                generation=gen,
                source_type=SourceType.RUST_CDYLIB,
                entry_symbol=target_symbol,
                code=wrapper_code,
                parent_id=parent_chromosome.id,
                compiled_artifact_path=lib_path,
                compiler_flags=["--crate-type", "cdylib", "-C", "opt-level=3"],
                mutation_meta={
                    "mutator": self.name,
                    "rust_source_path": rs_path,
                    "rust_code": rust_code,
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
        rust_to_ctypes = {
            "f64": "ctypes.c_double",
            "i64": "ctypes.c_longlong",
            "bool": "ctypes.c_bool",
        }

        arg_types = ", ".join(rust_to_ctypes.get(t, "ctypes.c_double") for _, t in arg_specs)
        res_type = rust_to_ctypes.get(return_type, "ctypes.c_double")

        param_names = [name for name, _ in arg_specs]
        param_sig = ", ".join(param_names)

        conversions = []
        for name, t in arg_specs:
            ctype_cls = rust_to_ctypes.get(t, "ctypes.c_double")
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
