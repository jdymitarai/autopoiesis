"""
Tests for Antigravity Cerebral Neural Cortex (SmolLM2-135M).

Verifies:
1. Model loading and configuration (~135M parameters).
2. Cognitive thinking (`think`) with latency and throughput tracking.
3. Cognitive self-reflection (`reflect`) and dream simulation (`dream`).
4. Procedural mutation candidate generation.
5. Fallback resilience when offline or when external dependencies are absent.
6. Cumulative telemetry tracking and snapshot state restoration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from autopoiesis.agent.cortex import (
    CortexReflection,
    CortexThought,
    NeuralCortex,
    SmolLM2Config,
    StandaloneTransformerFallback,
)
from autopoiesis.agent.metabolism import (
    EventType,
    ProceduralMutationCandidate,
    SessionEvent,
    TargetType,
)


class TestNeuralCortex:
    def test_cortex_initialization_defaults(self):
        cortex = NeuralCortex()
        assert cortex.model_id == "HuggingFaceTB/SmolLM2-135M"
        assert cortex.parameter_count == 134_516_736
        assert cortex.is_loaded is True
        assert cortex.active_backend in ("fallback_transformer", "transformers", "llama_cpp")
        assert cortex.total_inferences == 0
        assert cortex.total_tokens_generated == 0
        assert cortex.average_latency_ms == 0.0

    def test_cortex_think_basic_inference(self):
        cortex = NeuralCortex()
        thought = cortex.think("Verify metabolic integrity.", max_tokens=64)

        assert isinstance(thought, CortexThought)
        assert len(thought.text) > 0
        assert thought.tokens_generated > 0
        assert thought.prompt_tokens >= 1
        assert thought.latency_ms >= 0.0
        assert thought.tokens_per_second >= 0.0
        assert thought.backend == cortex.active_backend
        assert thought.model_id == cortex.model_id
        # String representation returns text
        assert str(thought) == thought.text

        # Dict serialization
        d = thought.to_dict()
        assert d["text"] == thought.text
        assert d["tokens_generated"] == thought.tokens_generated

    def test_cortex_think_edge_cases(self):
        cortex = NeuralCortex()

        # Empty prompt
        t_empty = cortex.think("")
        assert len(t_empty.text) > 0
        assert t_empty.tokens_generated >= 1

        # Whitespace prompt
        t_ws = cortex.think("   \n\t  ")
        assert len(t_ws.text) > 0

        # Boundary max_tokens = 1
        t_one = cortex.think("Single token test", max_tokens=1)
        assert t_one.tokens_generated == 1

        # Long prompt
        long_prompt = "operational context " * 200
        t_long = cortex.think(long_prompt, max_tokens=32)
        assert len(t_long.text) > 0
        assert t_long.tokens_generated <= 35

    def test_cortex_reflect_text_observation(self):
        cortex = NeuralCortex()
        reflection = cortex.reflect("Apoptotic Gate rejected mutation due to AST syntax corruption")

        assert isinstance(reflection, CortexReflection)
        assert "AST" in reflection.observation or "syntax" in reflection.observation
        assert len(reflection.insight) > 0
        assert reflection.confidence > 0.0
        assert reflection.latency_ms >= 0.0
        assert reflection.dream_simulation is not None

        # Mutation candidate dict structure
        cand = reflection.mutation_candidate
        assert cand is not None
        assert cand["target_type"] == "RULE"
        assert "mutation_type" in cand
        assert "content" in cand
        assert "rationale" in cand

        d = reflection.to_dict()
        assert d["insight"] == reflection.insight

    def test_cortex_reflect_dict_observation(self):
        cortex = NeuralCortex()
        obs = {
            "error": "Timeout during external foraging",
            "source_url": "https://example.com/api",
            "retry_count": 3,
        }
        reflection = cortex.reflect(obs)
        assert isinstance(reflection, CortexReflection)
        assert len(reflection.insight) > 0
        assert reflection.mutation_candidate is not None
        assert len(cortex.reflection_history) >= 1

    def test_cortex_dream_simulation(self):
        cortex = NeuralCortex()
        dream = cortex.dream()

        assert isinstance(dream, CortexThought)
        assert len(dream.text) > 0
        assert dream.tokens_generated > 0
        assert dream.latency_ms >= 0.0

        # Custom seed
        custom_dream = cortex.dream(seed="Simulate 100 concurrent agents accessing shared memory")
        assert len(custom_dream.text) > 0

    def test_cortex_generate_mutation_candidate(self):
        cortex = NeuralCortex()
        cand = cortex.generate_mutation_candidate("Recurring memory leak in ternary forward pass")

        assert isinstance(cand, ProceduralMutationCandidate)
        assert cand.target_type == TargetType.RULE
        assert cand.confidence >= 0.5
        assert len(cand.content) > 0
        assert len(cand.rationale) > 0
        assert cand.candidate_id is not None

    def test_cortex_metrics_tracking_and_reset(self):
        cortex = NeuralCortex()
        cortex.reset_metrics()

        assert cortex.total_inferences == 0
        assert cortex.total_tokens_generated == 0

        # Run 3 inferences
        cortex.think("First thought", max_tokens=16)
        cortex.think("Second thought", max_tokens=16)
        cortex.reflect("Third observation")

        assert cortex.total_inferences == 3
        assert cortex.total_tokens_generated > 0
        assert cortex.average_latency_ms >= 0.0
        assert cortex.last_inference_latency_ms >= 0.0

        # Reset
        cortex.reset_metrics()
        assert cortex.total_inferences == 0
        assert cortex.total_tokens_generated == 0
        assert cortex.average_latency_ms == 0.0
        assert len(cortex.reflection_history) == 0

    def test_cortex_serialization_and_restore(self):
        cortex = NeuralCortex()
        cortex.think("Generate tokens for telemetry state.")
        status = cortex.get_status()

        assert status["model_id"] == "HuggingFaceTB/SmolLM2-135M"
        assert status["parameters_count"] == 134_516_736
        assert status["total_inferences"] >= 1
        assert status["is_loaded"] is True

        # Restore into another instance
        cortex2 = NeuralCortex()
        cortex2.restore_status(status)
        assert cortex2.total_inferences == status["total_inferences"]
        assert cortex2.total_tokens_generated == status["total_tokens_generated"]

    def test_cortex_benchmark_harness(self):
        cortex = NeuralCortex()
        results = cortex.benchmark(iterations=3)

        assert results["model_id"] == "HuggingFaceTB/SmolLM2-135M"
        assert results["parameters_count"] == 134_516_736
        assert results["iterations"] == 3
        assert results["total_tokens"] > 0
        assert results["mean_latency_ms"] >= 0.0
        assert results["mean_tokens_per_sec"] >= 0.0
        assert results["is_loaded"] is True

    def test_cortex_fallback_resilience(self):
        # Force fallback by requesting non-existent backend and missing path
        cortex = NeuralCortex(
            backend_preference="invalid_backend",
            model_path="/non_existent/path/model.gguf",
        )
        assert cortex.is_loaded is True
        assert cortex.active_backend == "fallback_transformer"

        thought = cortex.think("Resilience verification under degraded environment.")
        assert len(thought.text) > 0
        assert thought.tokens_generated > 0

    def test_standalone_transformer_fallback_core(self):
        cfg = SmolLM2Config()
        core = StandaloneTransformerFallback(cfg)

        tokens = core.tokenize("Hello living organism world")
        assert len(tokens) >= 3

        att_score = core.forward_attention_step(seq_len=8)
        assert isinstance(att_score, float)

        text, n_tok = core.synthesize("error recovery analysis", max_tokens=32)
        assert len(text) > 0
        assert n_tok <= 35
