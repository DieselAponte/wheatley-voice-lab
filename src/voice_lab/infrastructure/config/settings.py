"""Centralized application settings using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central configuration for Wheatley Voice Lab."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API credentials and models
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    # Local directories
    data_dir: Path = Field(default=Path("data"), alias="DATA_DIR")
    reference_dir: Path = Field(default=Path("data/references"), alias="REFERENCE_DIR")
    generated_dir: Path = Field(default=Path("data/generated"), alias="GENERATED_DIR")
    evaluation_dir: Path = Field(default=Path("data/evaluations"), alias="EVALUATION_DIR")

    # Source and network configuration
    source_base_url: str = Field(
        default="https://theportalwiki.com/wiki/Wheatley_voice_lines/es",
        alias="SOURCE_BASE_URL",
    )
    http_timeout_seconds: float = Field(default=30.0, alias="HTTP_TIMEOUT_SECONDS")
    http_request_delay_seconds: float = Field(
        default=1.5, alias="HTTP_REQUEST_DELAY_SECONDS"
    )
    max_download_bytes: int = Field(default=25_000_000, alias="MAX_DOWNLOAD_BYTES")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Privacy safety controls: do not send reference audios to external APIs without explicit opt-in
    allow_reference_external_eval: bool = Field(
        default=False, alias="ALLOW_REFERENCE_EXTERNAL_EVAL"
    )

    def ensure_directories(self) -> None:
        """Create required local directories if they do not exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "metadata").mkdir(parents=True, exist_ok=True)
        self.reference_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.evaluation_dir.mkdir(parents=True, exist_ok=True)


# Singleton instance
settings = AppSettings()
