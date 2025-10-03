import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # noqa: F401


def _load_secrets_env():
    secrets_dir = Path(__file__).resolve().parent / ".secrets"
    if not secrets_dir.exists():
        # repo structure fallback: eaia/.secrets
        secrets_dir = Path(__file__).resolve().parents[1] / "eaia" / ".secrets"

    env_path = secrets_dir / ".env"
    if load_dotenv and env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=False)

    # Map GEMINI_API_KEY to GOOGLE_API_KEY if needed for Google GenAI SDKs
    if os.getenv("GOOGLE_API_KEY") in (None, ""):
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            os.environ["GOOGLE_API_KEY"] = gemini_key


_load_secrets_env()


