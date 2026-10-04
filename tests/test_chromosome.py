import json
import pytest
from autopoiesis.core.chromosome import Chromosome, LineageDAG, MutationRecord, SourceType


def test_chromosome_creation_and_hashing():
    code = "def foo(x): return x * 2"
    chrom1 = Chromosome.create(
        generation=1,
        source_type=SourceType.PYTHON_AST,
        entry_symbol="foo",
        code=code,
    )
    assert chrom1.id is not None
    assert len(chrom1.id) == 16
    assert chrom1.generation == 1
    assert chrom1.source_type == SourceType.PYTHON_AST
    assert chrom1.entry_symbol == "foo"
    assert chrom1.fitness == 1.0


def test_chromosome_serialization():
    chrom = Chromosome.create(
        generation=2,
        source_type=SourceType.C_EXTENSION,
        entry_symbol="compute",
        code="/* C code */",
        parent_id="abc123",
        compiled_artifact_path="/tmp/lib.so",
        compiler_flags=["-O3", "-shared"],
        fitness=15.4,
    )
    data = chrom.to_dict()
    assert data["source_type"] == "C_EXTENSION"
    assert data["fitness"] == 15.4

    restored = Chromosome.from_dict(data)
    assert restored.id == chrom.id
    assert restored.source_type == SourceType.C_EXTENSION
    assert restored.fitness == 15.4
    assert restored.parent_id == "abc123"


def test_lineage_dag():
    dag = LineageDAG()
    c0 = Chromosome.create(0, SourceType.PYTHON_AST, "f", "code0")
    c1 = Chromosome.create(1, SourceType.PYTHON_AST, "f", "code1", parent_id=c0.id)
    c2 = Chromosome.create(2, SourceType.RUST_CDYLIB, "f", "code2", parent_id=c1.id)

    dag.add_chromosome(c0, set_active=True)
    dag.add_chromosome(c1, set_active=True)
    dag.add_chromosome(c2, set_active=True)

    dag.record_mutation(
        MutationRecord(
            parent_id=c1.id,
            candidate_id="deadbeef",
            generation=2,
            mutator_name="bad_mutator",
            target_symbol="f",
            accepted=False,
            speedup=0.0,
            rejection_reason="FATAL_SEGFAULT",
        )
    )

    assert dag.get_active().id == c2.id
    ancestors = dag.get_ancestors(c2.id)
    assert len(ancestors) == 3
    assert ancestors[0].id == c0.id
    assert ancestors[1].id == c1.id
    assert ancestors[2].id == c2.id

    ascii_tree = dag.render_ascii_tree()
    assert "Gen 0" in ascii_tree
    assert "Gen 2" in ascii_tree
    assert "FATAL_SEGFAULT" in ascii_tree

    json_str = dag.to_json()
    parsed = json.loads(json_str)
    assert c2.id in parsed["chromosomes"]
    assert len(parsed["mutation_history"]) == 1
