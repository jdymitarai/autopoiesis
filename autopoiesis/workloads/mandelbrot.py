"""
Mandelbrot Fractal Computation Workload.

Contains the escape-time numeric calculation kernel and test vector suite.
"""

from __future__ import annotations

from typing import Any, List, Tuple


def mandelbrot_pixel(cr: float, ci: float, max_iter: int) -> int:
    """Escape-time Mandelbrot calculation for a single complex coordinate."""
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


def generate_mandelbrot_test_vectors() -> List[Tuple[tuple, dict]]:
    """Generates deterministic and edge-case test vectors."""
    vectors: List[Tuple[tuple, dict]] = [
        # Center inside main cardioid
        ((0.0, 0.0, 100), {}),
        # Points clearly outside
        ((2.0, 2.0, 100), {}),
        ((-2.5, 0.0, 100), {}),
        ((0.0, 1.5, 100), {}),
        # Boundary points (fractal filaments)
        ((-0.75, 0.1, 200), {}),
        ((-0.743643887037158704752191506114774, 0.131825904205311970493132056385139, 200), {}),
        ((-0.8, 0.156, 150), {}),
        ((0.285, 0.01, 150), {}),
        # Edge cases
        ((0.0, 0.0, 0), {}),
        ((0.0, 0.0, 1), {}),
    ]

    # Add systematic grid sampling
    for r_step in range(10):
        cr = -2.0 + (r_step * 0.3)
        for i_step in range(10):
            ci = -1.2 + (i_step * 0.24)
            vectors.append(((cr, ci, 100), {}))

    return vectors
