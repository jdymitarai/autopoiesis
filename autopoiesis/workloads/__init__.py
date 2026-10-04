"""
Benchmark workloads and test vector generators.
"""

from autopoiesis.workloads.mandelbrot import mandelbrot_pixel, generate_mandelbrot_test_vectors
from autopoiesis.workloads.nbody import nbody_pairwise_accel, generate_nbody_test_vectors

__all__ = [
    "mandelbrot_pixel",
    "generate_mandelbrot_test_vectors",
    "nbody_pairwise_accel",
    "generate_nbody_test_vectors",
]
