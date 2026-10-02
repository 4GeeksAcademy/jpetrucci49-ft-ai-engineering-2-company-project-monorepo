"""OpenAPI documents stay off unless an operator opts in."""

from app.core.config import expose_api_docs
from app.main import app


def test_api_docs_are_closed_by_default(monkeypatch) -> None:
    monkeypatch.delenv("HEALTHCORE_EXPOSE_DOCS", raising=False)
    assert expose_api_docs() is False
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
