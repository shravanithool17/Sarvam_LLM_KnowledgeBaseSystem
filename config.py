"""
config.py — Centralised configuration for the AI Knowledge Engineering Platform.

All runtime values are read from environment variables via python-dotenv.
Safe defaults ensure the application starts without any .env file.

Sarvam AI API — verified against official documentation (docs.sarvam.ai):
  - Primary authentication header: "api-subscription-key: <key>"
  - Secondary / OpenAI-compat header: "Authorization: Bearer <key>"
    (Both are accepted; api-subscription-key is preferred per official guidance.)
  - Valid model identifiers (as of 2025):
      "sarvam-105b"                — 128K context, complex reasoning & agentic tasks
      "sarvam-105b-conversations"  — 32K context, real-time conversational / voice-agent
    Note: "sarvam-30b" and "sarvam-2b" referenced in older docs are NOT valid identifiers
    on the current API and must not be used.
  - Endpoint: https://api.sarvam.ai/v1/chat/completions
  - Default temperature (per API docs): 0.2
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Load .env from the project root (file adjacent to this module)
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)


def _get_origins(raw: str) -> List[str]:
    """Parse a comma-separated ALLOWED_ORIGINS string into a list."""
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


class Settings:
    """
    Central settings object. Read once at module import time.
    Access via the module-level `settings` singleton.
    """

    # ------------------------------------------------------------------
    # Sarvam AI
    # ------------------------------------------------------------------
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "").strip()
    sarvam_model: str = os.getenv("SARVAM_MODEL", "sarvam-105b").strip()
    sarvam_api_url: str = os.getenv(
        "SARVAM_API_URL", "https://api.sarvam.ai/v1/chat/completions"
    ).strip()
    sarvam_timeout: int = int(os.getenv("SARVAM_TIMEOUT", "90"))
    sarvam_max_retries: int = int(os.getenv("SARVAM_MAX_RETRIES", "2"))

    # Valid Sarvam model identifiers — verified against docs.sarvam.ai
    VALID_SARVAM_MODELS: List[str] = [
        "sarvam-105b",
        "sarvam-105b-conversations",
    ]

    # ------------------------------------------------------------------
    # Document processing
    # ------------------------------------------------------------------
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
    default_chunk_size: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "600"))
    default_overlap: int = int(os.getenv("DEFAULT_OVERLAP", "100"))
    min_chunk_length: int = int(os.getenv("MIN_CHUNK_LENGTH", "50"))
    synthesis_batch_size: int = int(os.getenv("SYNTHESIS_BATCH_SIZE", "3"))
    default_num_facts: int = int(os.getenv("DEFAULT_NUM_FACTS", "3"))
    default_num_qa_pairs: int = int(os.getenv("DEFAULT_NUM_QA_PAIRS", "3"))

    # ------------------------------------------------------------------
    # RAG
    # ------------------------------------------------------------------
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", "2"))
    rag_min_score: float = float(os.getenv("RAG_MIN_SCORE", "0.0"))

    # ------------------------------------------------------------------
    # Quality / deduplication
    # ------------------------------------------------------------------
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.45"))

    # ------------------------------------------------------------------
    # Persistent storage
    # ------------------------------------------------------------------
    storage_dir: str = os.getenv("STORAGE_DIR", "./data/")

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    environment: str = os.getenv("ENVIRONMENT", "development").strip().lower()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    # CORS: wildcard only in development; production must set explicit origins.
    _raw_origins: str = os.getenv("ALLOWED_ORIGINS", "")
    allowed_origins: List[str] = (
        ["*"]
        if os.getenv("ENVIRONMENT", "development").strip().lower() == "development"
        and not os.getenv("ALLOWED_ORIGINS", "").strip()
        else _get_origins(os.getenv("ALLOWED_ORIGINS", ""))
    )

    def has_api_key(self) -> bool:
        """Returns True if a non-placeholder Sarvam API key is configured."""
        return bool(
            self.sarvam_api_key
            and self.sarvam_api_key != "your_sarvam_api_key_here"
        )

    def resolve_model(self, requested: str) -> str:
        """
        Returns a validated Sarvam model identifier.
        Falls back to the configured default if `requested` is not a known valid model.
        """
        if requested in self.VALID_SARVAM_MODELS:
            return requested
        # Fall back to configured default (which may itself need validation)
        if self.sarvam_model in self.VALID_SARVAM_MODELS:
            return self.sarvam_model
        return "sarvam-105b"

    def __repr__(self) -> str:
        """Never expose the API key value in repr output."""
        masked = "***" if self.sarvam_api_key else "<not set>"
        return (
            f"Settings(model={self.sarvam_model!r}, "
            f"api_key={masked}, "
            f"environment={self.environment!r}, "
            f"log_level={self.log_level!r})"
        )


# Module-level singleton — import this everywhere.
settings = Settings()
