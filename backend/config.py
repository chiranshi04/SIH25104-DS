"""
config.py
---------
Yahan hum saari app-level settings ek jagah rakhte hain.
Isse hum kabhi bhi database URL, secret keys, etc. ko
hard-code nahi karenge — sab .env file se aayega.
"""

import os
from dotenv import load_dotenv

# .env file ko load karo (agar exist karti hai)
load_dotenv()


class Settings:
    # App info
    APP_NAME: str = "SIH25104 - Language Agnostic Chatbot"
    APP_VERSION: str = "0.1.0"

    # Environment (development / production)
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"
        ).split(",")
        if origin.strip()
    ]
    DOCS_ENABLED: bool = os.getenv("DOCS_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }
    MAX_CHAT_BODY_BYTES: int = int(os.getenv("MAX_CHAT_BODY_BYTES", "10240"))

    # PostgreSQL connection Phase 6 se required hai
    DATABASE_URL: str = os.getenv("DATABASE_URL", "").strip()
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and configure PostgreSQL."
        )

    # Yeh hum Phase 8 mein use karenge (JWT)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-later")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )

    # Admin seed script ke credentials .env se aayenge
    ADMIN_NAME: str = os.getenv("ADMIN_NAME", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")

    # Documents frontend folder ke bahar store honge
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "10"))
    # Student 1 adapter mode: dummy (development), http, or module
    AI_MODE: str = os.getenv("AI_MODE", "dummy").strip().lower()
    AI_BASE_URL: str = os.getenv("AI_BASE_URL", "").strip().rstrip("/")
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    AI_MODULE_PATH: str = os.getenv("AI_MODULE_PATH", "").strip()

    def validate_security(self) -> None:
        if self.ENVIRONMENT.lower() != "production":
            return
        if self.SECRET_KEY == "dev-secret-change-later" or len(self.SECRET_KEY) < 32:
            raise RuntimeError(
                "Production startup refused: SECRET_KEY must be a random value of at least 32 characters."
            )
        if self.AI_MODE == "dummy":
            raise RuntimeError(
                "Production startup refused: AI_MODE=dummy is not allowed. Configure http or module."
            )
        if "*" in self.CORS_ORIGINS:
            raise RuntimeError(
                "Production startup refused: CORS_ORIGINS must not contain '*'."
            )


# Ek hi settings object poore app mein use hoga
settings = Settings()
