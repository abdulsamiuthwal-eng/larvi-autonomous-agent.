"""
Larvi — Configuration Manager
Loads and validates all environment variables from .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Central settings object for Larvi application."""

    # ── LLM ──────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ── Google OAuth ──────────────────────────────────────────────────────
    GOOGLE_CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "credentials.json"
    )
    GOOGLE_TOKEN_PATH: str = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    # Direct env-var credentials (set via Vercel Environment Variables — never hardcode here)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "https://larvi-autonomous-agent.vercel.app/auth/callback"
    )
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "https://larvi-autonomous-agent.vercel.app"
    )

    # Gmail + Calendar + UserInfo OAuth scopes
    GOOGLE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]

    # ── App ───────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "larvi-dev-secret-change-in-prod")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── CORS ──────────────────────────────────────────────────────────────
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

    # ── LLM Model ─────────────────────────────────────────────────────────
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODELS: list[str] = [
        "gemini-3.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
    ]

    def validate(self) -> None:
        """Check that critical keys are set before app starts."""
        errors = []
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY == "your_gemini_api_key_here":
            errors.append("GEMINI_API_KEY is not set in .env file.")
        cred_path = BASE_DIR / self.GOOGLE_CREDENTIALS_PATH
        if not cred_path.exists():
            errors.append(
                f"credentials.json not found at: {cred_path}\n"
                "  → Download from Google Cloud Console and place in /backend folder."
            )
        if errors:
            print("\n" + "═" * 60)
            print("  ⚠  LARVI CONFIGURATION WARNINGS")
            print("═" * 60)
            for e in errors:
                print(f"  • {e}")
            print("═" * 60 + "\n")


settings = Settings()
