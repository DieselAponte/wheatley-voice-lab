"""Domain models for synthetic speech generations and experiment records."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GenerationRecord(BaseModel):
    """Complete metadata record of a synthesized speech experiment."""

    model_config = ConfigDict(extra="ignore")

    generation_id: str = Field(description="Unique stable ID of the generation (e.g. gen_abcd1234).")
    text: str = Field(description="Original input text synthesized.")
    profile_id: str = Field(description="Applied expressive emotion profile ID.")
    profile_name: str = Field(description="Human-readable profile display name.")
    parameters: dict[str, float] = Field(default_factory=dict, description="Inference parameters used.")

    # Voice prompt reference
    reference_audio_id: Optional[str] = Field(default=None, description="Reference audio ID used for voice cloning.")
    reference_audio_path: Optional[str] = Field(default=None, description="Path to reference audio clip if provided.")

    # Technical audio attributes
    audio_path: str = Field(description="Relative or absolute path to generated WAV file.")
    audio_sha256: str = Field(default="", description="SHA-256 hash of the generated audio.")
    duration_seconds: float = Field(default=0.0, description="Duration in seconds.")
    file_size_bytes: int = Field(default=0, description="Size in bytes.")
    sample_rate_hz: int = Field(default=24000, description="Sampling rate in Hz.")

    # Execution provenance
    model_name: str = Field(default="ResembleAI/Chatterbox-Multilingual-es-es", description="TTS model name.")
    generator_device: str = Field(default="cpu", description="Compute device utilized (cuda, cpu).")
    status: str = Field(default="SUCCESS", description="Execution status (SUCCESS, FAILED).")
    error_message: Optional[str] = Field(default=None, description="Error detail if generation failed.")

    # Associated evaluations
    evaluation_ids: list[str] = Field(default_factory=list, description="IDs of linked evaluations.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GenerationComparison(BaseModel):
    """Structured side-by-side comparison between multiple generations."""

    model_config = ConfigDict(extra="ignore")

    records: list[GenerationRecord]
    has_same_text: bool
    unique_profiles: list[str]
    duration_range_seconds: tuple[float, float]
    summary_text: str
