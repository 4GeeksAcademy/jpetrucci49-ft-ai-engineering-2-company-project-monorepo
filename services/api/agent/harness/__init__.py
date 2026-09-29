"""Stacked desk-agent harness: input, isolate, output. Not a single filter."""

from agent.harness.classify import InputLabel, classify_input
from agent.harness.input_guard import apply_input_guard
from agent.harness.isolate import wrap_context, wrap_text
from agent.harness.observe import reset_counts, summary

__all__ = [
    "InputLabel",
    "apply_input_guard",
    "classify_input",
    "reset_counts",
    "summary",
    "wrap_context",
    "wrap_text",
]
