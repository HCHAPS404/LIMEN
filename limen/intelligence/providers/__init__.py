"""Vendor LLM adapters. Only this package may import vendor SDKs."""

from limen.intelligence.providers.factory import build_llm_provider

__all__ = ["build_llm_provider"]
