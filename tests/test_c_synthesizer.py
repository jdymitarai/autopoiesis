import ast
import pytest
from autopoiesis.mutators.c_synthesizer import ASTToCTranspiler, CSynthesizerMutator
from autopoiesis.workloads.mandelbrot import mandelbrot_pixel
from autopoiesis.workloads.nbody import nbody_pairwise_accel


def test_ast_to_c_transpilation_mandelbrot():
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
    transpiler = ASTToCTranspiler(target_func_name="mandelbrot_pixel")
    c_code, args, return_type = transpiler.transpile(tree)

    assert "EXPORT" in c_code
    assert "mandelbrot_pixel" in c_code
    assert "double cr" in c_code
    assert "double ci" in c_code
    assert "int64_t max_iter" in c_code
    assert "for (int64_t i = 0; i < max_iter; i++)" in c_code
    assert "(zr2 + zi2) > 4.0" in c_code
    assert len(args) == 3


def test_ast_to_c_transpilation_nbody():
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
    transpiler = ASTToCTranspiler(target_func_name="nbody_pairwise_accel")
    c_code, args, return_type = transpiler.transpile(tree)

    assert "sqrt(dist_sq)" in c_code
    assert "return (double)" in c_code
    assert len(args) == 8


def test_c_synthesizer_wrapper_generation():
    mut = CSynthesizerMutator(compiler="nonexistent_compiler")
    wrapper = mut._generate_ctypes_wrapper(
        target_symbol="mandelbrot_pixel",
        arg_specs=[("cr", "double"), ("ci", "double"), ("max_iter", "int64_t")],
        return_type="int64_t",
    )
    assert "_c_func.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_longlong]" in wrapper
    assert "_c_func.restype = ctypes.c_longlong" in wrapper
    assert "def mandelbrot_pixel(cr, ci, max_iter):" in wrapper


def test_c_variable_scoping_in_conditionals():
    source = """
def check_sign(x: float) -> float:
    if x > 0:
        val = 1.0
    else:
        val = -1.0
    return val
"""
    tree = ast.parse(source)
    transpiler = ASTToCTranspiler(target_func_name="check_sign")
    c_code, args, return_type = transpiler.transpile(tree)

    assert "double val = 0.0;" in c_code
    assert "val = 1.0;" in c_code
    assert "val = (-1.0);" in c_code
    assert return_type == "double"


def test_c_control_flow_break_continue():
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
    transpiler = ASTToCTranspiler(target_func_name="loop_test")
    c_code, args, return_type = transpiler.transpile(tree)

    assert "continue;" in c_code
    assert "break;" in c_code
