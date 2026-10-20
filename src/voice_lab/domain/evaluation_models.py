"""Domain models for structured audio evaluation."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AudioEvaluation(BaseModel):
    """Structured perception report returned by an audio evaluator."""

    model_config = ConfigDict(extra="ignore")

    evaluation_id: str = Field(description="Unique identifier for this evaluation event.")
    audio_id: str = Field(description="Identifier of the audio clip evaluated.")
    audio_sha256: str = Field(description="SHA-256 hash of the evaluated audio data.")
    is_reference_audio: bool = Field(default=False, description="True if audio is an original reference clip.")

    # Linguistic and perceptual observations
    estimated_transcript: Optional[str] = Field(default=None, description="Transcribed dialogue.")
    perceived_language: str = Field(default="es-ES", description="Perceived language/accent.")
    perceived_emotion: str = Field(
        default="conversacional",
        description="Perceived primary expression (conversacional, entusiasmado, confundido, enfadado, nervioso, sarcástico, etc.).",
    )
    secondary_emotions: list[str] = Field(default_factory=list, description="Secondary emotional nuances.")
    expressive_intensity: float = Field(ge=1.0, le=5.0, default=3.0, description="Perceived expressive intensity (1 to 5).")
    intelligibility_score: float = Field(ge=1.0, le=5.0, default=4.0, description="Perceived speech clarity (1 to 5).")
    prosody_notes: str = Field(default="", description="Observations on rhythm, pacing, pauses, and pitch erraticism.")
    vocal_characteristics: str = Field(default="", description="Acoustic vocal coloring (e.g. robotic filter, breathless, robotic glitch).")
    confidence: float = Field(ge=0.0, le=1.0, default=0.8, description="Evaluator certainty score.")
    explanation: str = Field(default="", description="Explanatory text supporting the evaluation.")
    uncertainties: list[str] = Field(default_factory=list, description="Dimensions that could not be reliably evaluated.")

    # Execution provenance
    evaluator_provider: str = Field(default="google-genai", description="Provider name (google-genai, mock, etc.).")
    evaluator_model: str = Field(default="gemini-2.5-flash", description="Model identifier used for inference.")
    prompt_version: str = Field(default="v1.0", description="Evaluation prompt version.")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
