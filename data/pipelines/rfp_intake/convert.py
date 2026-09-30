"""PDF → Markdown via MarkItDown, then PHI redact, before any agent reads the text."""

from __future__ import annotations

from pathlib import Path

from agent.memory.phi import redact_phi
from data.pipelines.paths import RAW_DIR
from data.pipelines.rfp_intake.extracts import extract_metadata
from data.pipelines.rfp_intake.readability import compute_readability

RFP_RAW_DIR = RAW_DIR / "rfp"


def pdf_to_markdown(pdf_path: str | Path) -> str:
    from markitdown import MarkItDown
    from markitdown._exceptions import FileConversionException, MissingDependencyException

    try:
        result = MarkItDown().convert(str(pdf_path))
    except MissingDependencyException as exc:
        raise RuntimeError(
            "MarkItDown PDF extras are missing. Install with: uv add 'markitdown[pdf]'"
        ) from exc
    except FileConversionException as exc:
        detail = str(exc).lower()
        if "have not been installed" in detail or "optional dependency" in detail:
            raise RuntimeError(
                "MarkItDown PDF extras are missing. Install with: uv add 'markitdown[pdf]'"
            ) from exc
        raise
    return (getattr(result, "text_content", None) or "").strip()


def convert_document(
    *,
    ticket_id: str,
    pdf_path: str,
    markdown: str | None = None,
) -> dict:
    """Convert (or accept pre-supplied Markdown), redact PHI, persist ``.md``, extract metadata."""
    text = (markdown or "").strip() or pdf_to_markdown(pdf_path)
    redacted, phi_detected = redact_phi(text)
    RFP_RAW_DIR.mkdir(parents=True, exist_ok=True)
    md_path = RFP_RAW_DIR / f"{ticket_id}.md"
    md_path.write_text(redacted, encoding="utf-8")
    metadata = extract_metadata(redacted)
    metadata["readability"] = compute_readability(redacted)
    return {
        "markdown": redacted,
        "markdown_path": str(md_path),
        "phi_detected": phi_detected,
        "metadata": metadata,
    }
