import os


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3001",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
