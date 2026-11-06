import os


def csv_env(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tt.db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
FRONTEND_ORIGINS = csv_env("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:5174")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")


def validate_config() -> None:
    if len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be configured with at least 32 characters")
    if ACCESS_TOKEN_EXPIRE_MINUTES < 1:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
