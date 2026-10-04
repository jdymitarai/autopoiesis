"""
N-Body Gravitational Interaction Workload.
"""

from __future__ import annotations

import math
from typing import Any, List, Tuple


def nbody_pairwise_accel(
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
    mass2: float, softening: float,
) -> float:
    """Computes scalar gravitational acceleration contribution between two bodies."""
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1
    dist_sq = dx * dx + dy * dy + dz * dz + softening * softening
    dist = math.sqrt(dist_sq)
    inv_dist_cube = 1.0 / (dist * dist * dist)
    return mass2 * inv_dist_cube


def nbody_simulation_energy(n: int, steps: int) -> float:
    """Simulates N-body system interaction and computes total potential energy proxy."""
    energy = 0.0
    softening = 0.01
    for s in range(steps):
        for i in range(n):
            xi = float(i) * 0.1
            yi = float(i) * 0.2
            zi = float(i) * 0.3
            for j in range(n):
                if i != j:
                    xj = float(j) * 0.1
                    yj = float(j) * 0.2
                    zj = float(j) * 0.3
                    dx = xj - xi
                    dy = yj - yi
                    dz = zj - zi
                    dist_sq = (dx * dx) + (dy * dy) + (dz * dz) + (softening * softening)
                    dist = math.sqrt(dist_sq)
                    energy += 1.0 / dist
    return energy


def generate_nbody_test_vectors() -> List[Tuple[tuple, dict]]:
    """Generates test vectors for N-body simulation."""
    return [
        ((5, 2), {}),
        ((10, 2), {}),
        ((15, 3), {}),
        ((20, 2), {}),
    ]
