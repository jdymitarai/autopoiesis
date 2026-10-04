"""
Atomic In-Memory Hot-Swapping Engine.

Replaces living function implementations and module bindings in-memory without
restarting the running process. Maintains an undo stack for instantaneous rollback.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from autopoiesis.core.chromosome import Chromosome, SourceType


class AtomicHotSwapper:
    """Thread-safe, atomic module hot-swapper with rollback guarantees."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # History map: symbol_key -> List[Callable]
        self._history: Dict[str, List[Callable[..., Any]]] = {}
        # Active chromosome map: symbol_key -> Chromosome
        self._active_chromosomes: Dict[str, Chromosome] = {}
        # Loaded shared libraries to prevent garbage collection unloading
        self._loaded_cdlls: List[ctypes.CDLL] = []

    def _make_key(self, target_module: Any, symbol_name: str) -> str:
        mod_name = target_module.__name__ if hasattr(target_module, "__name__") else str(target_module)
        return f"{mod_name}::{symbol_name}"

    def build_callable_from_chromosome(
        self,
        chromosome: Chromosome,
        module_dict: Optional[Dict[str, Any]] = None,
    ) -> Callable[..., Any]:
        """Instantiates a live Python callable from a Chromosome specification."""
        import math
        base_env: Dict[str, Any] = {"math": math, "sys": sys, "os": os}
        if module_dict:
            base_env.update({k: v for k, v in module_dict.items() if not k.startswith("__")})

        if chromosome.source_type == SourceType.PYTHON_AST:
            namespace: Dict[str, Any] = dict(base_env)
            exec(chromosome.code, namespace)
            if chromosome.entry_symbol not in namespace:
                raise KeyError(
                    f"Entry symbol '{chromosome.entry_symbol}' not found in compiled Python AST."
                )
            return namespace[chromosome.entry_symbol]

        elif chromosome.source_type in (SourceType.C_EXTENSION, SourceType.RUST_CDYLIB):
            if not chromosome.compiled_artifact_path or not os.path.exists(chromosome.compiled_artifact_path):
                raise FileNotFoundError(
                    f"Binary shared library artifact missing: {chromosome.compiled_artifact_path}"
                )

            # Load dynamic shared library
            cdll = ctypes.CDLL(chromosome.compiled_artifact_path)
            self._loaded_cdlls.append(cdll)

            namespace: Dict[str, Any] = {"ctypes": ctypes, "lib": cdll, "math": math}
            exec(chromosome.code, namespace)

            if chromosome.entry_symbol not in namespace:
                raise KeyError(
                    f"Entry symbol '{chromosome.entry_symbol}' not found in compiled ctypes binding wrapper."
                )
            return namespace[chromosome.entry_symbol]

        else:
            raise ValueError(f"Unsupported source type {chromosome.source_type}")

    def hot_swap(
        self,
        target_module: Any,
        symbol_name: str,
        chromosome: Chromosome,
    ) -> Callable[..., Any]:
        """
        Atomically swaps the living function implementation in target_module.
        Preserves rollback capability.
        """
        key = self._make_key(target_module, symbol_name)
        new_callable = self.build_callable_from_chromosome(
            chromosome,
            module_dict=getattr(target_module, "__dict__", None),
        )

        with self._lock:
            # Preserve current implementation on history stack
            current_impl = getattr(target_module, symbol_name, None)
            if key not in self._history:
                self._history[key] = []
            if current_impl is not None:
                self._history[key].append(current_impl)

            # Preserve root original source on the new wrapper so subsequent LivingOrganisms can inspect it
            orig_src = getattr(current_impl, "__autopoiesis_source__", None)
            if not orig_src and current_impl is not None:
                try:
                    import inspect
                    orig_src = inspect.getsource(current_impl)
                except Exception:
                    orig_src = None
            if orig_src:
                try:
                    setattr(new_callable, "__autopoiesis_source__", orig_src)
                except Exception:
                    pass

            # Atomic module dict update
            setattr(target_module, symbol_name, new_callable)
            self._active_chromosomes[key] = chromosome

        return new_callable

    def rollback(self, target_module: Any, symbol_name: str) -> Optional[Callable[..., Any]]:
        """Rolls back to the previous generation implementation."""
        key = self._make_key(target_module, symbol_name)

        with self._lock:
            if not self._history.get(key):
                return None  # No prior history to rollback to

            previous_callable = self._history[key].pop()
            setattr(target_module, symbol_name, previous_callable)
            return previous_callable

    def restore_initial(self, target_module: Any, symbol_name: str) -> Optional[Callable[..., Any]]:
        """Restores the initial unpatched implementation from the root of the history stack."""
        key = self._make_key(target_module, symbol_name)
        with self._lock:
            if not self._history.get(key):
                return None
            initial_callable = self._history[key][0]
            self._history[key].clear()
            setattr(target_module, symbol_name, initial_callable)
            self._active_chromosomes.pop(key, None)
            return initial_callable

    def unload_all(self) -> None:
        """Releases loaded shared dynamic libraries (FreeLibrary on Windows)."""
        import platform
        if platform.system() == "Windows":
            for cdll in self._loaded_cdlls:
                try:
                    if hasattr(cdll, "_handle") and cdll._handle:
                        ctypes.windll.kernel32.FreeLibrary(cdll._handle)
                except Exception:
                    pass
        self._loaded_cdlls.clear()

    def get_active_chromosome(self, target_module: Any, symbol_name: str) -> Optional[Chromosome]:
        key = self._make_key(target_module, symbol_name)
        return self._active_chromosomes.get(key)

