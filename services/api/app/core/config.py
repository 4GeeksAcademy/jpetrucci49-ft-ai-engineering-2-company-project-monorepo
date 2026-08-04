import os


def get_cors_origins() -> list[str]:
    """Explicit allow-list. Use CORS_ORIGINS=* for permissive local dev."""
    raw = os.getenv("CORS_ORIGINS", "")
    if raw.strip() == "*":
        return ["*"]
    default = (
        "http://localhost:3001,"
        "http://127.0.0.1:3001,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )
    configured = raw or default
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def get_cors_origin_regex() -> str | None:
    """Match Codespaces / GitHub Codespaces forwarded URLs."""
    return os.getenv(
        "CORS_ORIGIN_REGEX",
        r"https://.*\.(app\.github\.dev|github\.dev)",
    )
