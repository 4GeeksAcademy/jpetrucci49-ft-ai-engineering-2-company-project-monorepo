"""Readability metrics as a processing-cost signal, not a literary grade."""

from __future__ import annotations

import logging
import warnings

logger = logging.getLogger(__name__)

_NLTK_READY = False


def _ensure_nltk() -> None:
    global _NLTK_READY
    if _NLTK_READY:
        return
    import nltk

    for resource in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                logger.debug("nltk download skipped for %s", resource)
    _NLTK_READY = True


def compute_readability(text: str) -> dict[str, float]:
    """Return named scores from py-readability-metrics. Empty dict if text is too short."""
    blob = (text or "").strip()
    if len(blob.split()) < 50:
        return {}
    _ensure_nltk()
    try:
        # py-readability-metrics 1.4.x ships a regex with `\/` (Python 3.12 SyntaxWarning).
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=r"invalid escape sequence",
                category=SyntaxWarning,
                module=r"readability\.text\.analyzer",
            )
            from readability import Readability
    except ImportError:
        return {}

    try:
        reader = Readability(blob)
    except Exception:
        return {}

    metrics: dict[str, float] = {}
    extractors = (
        ("flesch_kincaid_grade", lambda: reader.flesch_kincaid().grade_level),
        ("flesch_reading_ease", lambda: reader.flesch().score),
        ("gunning_fog", lambda: reader.gunning_fog().score),
        ("smog", lambda: reader.smog().score),
        ("coleman_liau", lambda: reader.coleman_liau().score),
        ("ari", lambda: reader.ari().score),
    )
    for name, getter in extractors:
        try:
            metrics[name] = float(getter())
        except Exception:
            continue
    return metrics
