import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

def normalize_email(email: str) -> str:
    """Normalizes email address: lowercased, trimmed, strip +alias if present."""
    if not email:
        return ""
    email = email.strip().lower()
    if "@" in email:
        local, domain = email.split("@", 1)
        if "+" in local:
            local = local.split("+", 1)[0]
        return f"{local}@{domain}"
    return email

class Settings(BaseModel):
    CANDIDATE_ID: str = normalize_email(os.getenv("CANDIDATE_ID", ""))
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sales_inbox.db")
    MONGODB_URL: str = os.getenv("MONGODB_URL", os.getenv("MONGO_URI", ""))
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list = ["*"]

settings = Settings()
