"""PHASE 8 challenge evaluation harness — jury-style scenarios against real LIMEN APIs."""

from __future__ import annotations

from evals.challenge.runner import run_challenge_evaluation
from evals.challenge.scenarios import SCENARIOS

__all__ = ["SCENARIOS", "run_challenge_evaluation"]
