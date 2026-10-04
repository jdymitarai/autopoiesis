import ast
import shutil
import pytest
from autopoiesis.mutators.rust_synthesizer import ASTToRustTranspiler, RustSynthesizerMutator
from autopoiesis.core.chromosome import Chromosome, SourceType
from autopoiesis.core.hotspot import HotspotDetector


def test_ast_to_rust_transpilation_mandelbrot():
    source = """
def mandelbrot_pixel(cr: float, ci: float, max_iter: int) -> int:
    zr = 0.0
    zi = 0.0
    for i in range(max_iter):
        zr2 = zr * zr
        zi2 = zi * zi
        if zr2 + zi2 > 4.0:
            return i
        zi = 2.0 * zr * zi + ci
        zr = zr2 - zi2 + cr
    return max_iter
"""
    tree = ast.parse(source)
    transpiler = ASTToRustTranspiler(target_func_name="mandelbrot_pixel")
    rust_code, args, return_type = transpiler.transpile(tree)

    assert "pub extern \"C\" fn mandelbrot_pixel" in rust_code
    assert "mut cr: f64" in rust_code
    assert "mut ci: f64" in rust_code
    assert "mut max_iter: i64" in rust_code
    assert "-> i64" in rust_code
    assert "let mut zr: f64" in rust_code
    assert "let mut zi: f64" in rust_code
    assert "for i in (0 as i64)..(max_iter as i64)" in rust_code
    assert "return (max_iter) as i64" in rust_code
    assert return_type == "i64"
    assert len(args) == 3


def test_ast_to_rust_transpilation_nbody():
    source = """
def nbody_pairwise_accel(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float, mass2: float, softening: float) -> float:
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    dist_sq = dx * dx + dy * dy + dz * dz + softening * softening
    dist = math.sqrt(dist_sq)
    inv_dist_cube = 1.0 / (dist * dist * dist)
    return mass2 * inv_dist_cube
"""
    tree = ast.parse(source)
    transpiler = ASTToRustTranspiler(target_func_name="nbody_pairwise_accel")
    rust_code, args, return_type = transpiler.transpile(tree)

    assert "(dist_sq).sqrt()" in rust_code
    assert "mass2 * inv_dist_cube" in rust_code
    assert "return" in rust_code
    assert return_type == "f64"
    assert len(args) == 8


def test_rust_variable_scoping_in_conditionals():
    """Verifies that variables assigned inside conditional branches are hoisted to function scope."""
    source = """
def check_sign(x: float) -> float:
    if x > 0:
        val = 1.0
    else:
        val = -1.0
    return val
"""
    tree = ast.parse(source)
    transpiler = ASTToRustTranspiler(target_func_name="check_sign")
    rust_code, args, return_type = transpiler.transpile(tree)

    # val must be hoisted and declared before the if block
    assert "let mut val: f64 = 0.0_f64;" in rust_code
    # inside if/else, only assignment occurs
    assert "val = 1.0_f64;" in rust_code
    assert "val = (-1.0_f64);" in rust_code


def test_rust_control_flow_break_continue():
    source = """
def loop_test(n: int) -> int:
    acc = 0
    for i in range(n):
        if i == 2:
            continue
        if i == 5:
            break
        acc += i
    return acc
"""
    tree = ast.parse(source)
    transpiler = ASTToRustTranspiler(target_func_name="loop_test")
    rust_code, args, return_type = transpiler.transpile(tree)

    assert "continue;" in rust_code
    assert "break;" in rust_code


def test_rust_synthesizer_wrapper_generation():
    mut = RustSynthesizerMutator(rustc_path="dummy_rustc")
    wrapper = mut._generate_ctypes_wrapper(
        target_symbol="mandelbrot_pixel",
        arg_specs=[("cr", "f64"), ("ci", "f64"), ("max_iter", "i64")],
        return_type="i64",
    )
    assert "_c_func.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_longlong]" in wrapper
    assert "_c_func.restype = ctypes.c_longlong" in wrapper
    assert "def mandelbrot_pixel(cr, ci, max_iter):" in wrapper


@pytest.mark.skipif(shutil.which("rustc") is None, reason="rustc not installed on system")
def test_rust_compilation_and_execution(tmp_path):
    source = """
def multiply_add(a: float, b: float, c: float) -> float:
    return (a * b) + c
"""
    tree = ast.parse(source)
    profile = HotspotDetector.analyze_source_ast(source, "multiply_add")
    chrom = Chromosome.create(0, SourceType.PYTHON_AST, "multiply_add", source)

    mut = RustSynthesizerMutator()
    candidate = mut.mutate(chrom, profile, target_dir=str(tmp_path))

    assert candidate is not None
    assert candidate.compiled_artifact_path is not None
    assert candidate.source_type == SourceType.RUST_CDYLIB

    import ctypes
    cdll = ctypes.CDLL(candidate.compiled_artifact_path)
    ns = {"ctypes": ctypes, "lib": cdll}
    exec(candidate.code, ns)
    fn = ns["multiply_add"]

    assert fn(2.0, 3.0, 4.0) == 10.0
    assert fn(0.5, 4.0, 1.5) == 3.5
