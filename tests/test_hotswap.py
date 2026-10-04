import pytest
import types
from autopoiesis.core.hotswap import AtomicHotSwapper
from autopoiesis.core.chromosome import Chromosome, SourceType


def test_atomic_hot_swap_and_rollback():
    # Create dynamic mock module
    mod = types.ModuleType("mock_target")
    mod.compute = lambda x: x + 1

    swapper = AtomicHotSwapper()

    # Mutation Gen 1: multiplies by 2
    c1 = Chromosome.create(
        generation=1,
        source_type=SourceType.PYTHON_AST,
        entry_symbol="compute",
        code="def compute(x):\n    return x * 2\n",
    )

    new_fn = swapper.hot_swap(mod, "compute", c1)
    assert mod.compute(5) == 10
    assert swapper.get_active_chromosome(mod, "compute").id == c1.id

    # Mutation Gen 2: multiplies by 10
    c2 = Chromosome.create(
        generation=2,
        source_type=SourceType.PYTHON_AST,
        entry_symbol="compute",
        code="def compute(x):\n    return x * 10\n",
    )
    swapper.hot_swap(mod, "compute", c2)
    assert mod.compute(5) == 50

    # Rollback to Gen 1
    rolled_back = swapper.rollback(mod, "compute")
    assert rolled_back is not None
    assert mod.compute(5) == 10

    # Rollback to Gen 0
    swapper.rollback(mod, "compute")
    assert mod.compute(5) == 6  # 5 + 1
