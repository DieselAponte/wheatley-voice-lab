"""Gemini multimodal audio evaluator adapter using the official google-genai SDK."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from google import genai
from google.genai import types

from src.voice_lab.domain.contracts import AudioEvaluator
from src.voice_lab.domain.evaluation_models import AudioEvaluation
from src.voice_lab.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class GeminiAudioEvaluator(AudioEvaluator):
    """Evaluates audio clips using Google Gemini multimodal capabilities."""

    PROMPT_VERSION = "v1.0"
    SYSTEM_INSTRUCTION = (
        "Actúa como un fonetista y lingüista experto en español de España. "
        "Analiza el clip de audio adjunto de voz en castellano. "
        "Distingue cuidadosamente entre características acústicas audibles y la expresión percibida. "
        "No asumas emociones internas absolutas; reporta la impresión auditiva y los rasgos de prosodia observados."
    )

    EVAL_PROMPT = """
Analiza este audio y devuelve un JSON estricto con las siguientes propiedades:
{
  "estimated_transcript": "Transcripción textual del audio en español.",
  "perceived_language": "es-ES",
  "perceived_emotion": "Una de: conversacional, entusiasmado, confundido, enfadado, nervioso, sarcástico, u otra observación descriptiva",
  "secondary_emotions": ["emociones secundarias si existen"],
  "expressive_intensity": 3.5, // Número decimal de 1.0 a 5.0
  "intelligibility_score": 4.5, // Número decimal de 1.0 a 5.0
  "prosody_notes": "Observaciones detalladas sobre el ritmo, pausas, énfasis, tempo y tono.",
  "vocal_characteristics": "Rasgos vocales audibles (filtro robótico, respiración, velocidad errática, etc.)",
  "confidence": 0.85, // Certeza de 0.0 a 1.0
  "explanation": "Explicación concisa y evidencia auditiva concreta que respalde las observaciones.",
  "uncertainties": ["aspectos dudosos o no evaluables"]
}
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model
        if not self.api_key:
            logger.warning("GeminiAudioEvaluator initialized without GEMINI_API_KEY. Calls will fail unless simulated.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def evaluate(
        self,
        audio_path: Path,
        audio_id: str,
        audio_sha256: str,
        is_reference: bool = False,
        expected_transcript: Optional[str] = None,
    ) -> AudioEvaluation:
        """Upload/stream audio to Gemini and return structured evaluation."""
        if not self.client:
            raise ValueError(
                "GEMINI_API_KEY is not configured in environment or .env. "
                "Configure a valid key or use MockAudioEvaluator / simulate=True."
            )

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file to evaluate not found: {audio_path}")

        audio_bytes = audio_path.read_bytes()
        mime_type = "audio/wav"
        if audio_path.suffix.lower() == ".mp3":
            mime_type = "audio/mp3"
        elif audio_path.suffix.lower() == ".ogg":
            mime_type = "audio/ogg"

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        prompt_text = self.EVAL_PROMPT
        if expected_transcript:
            prompt_text += f"\nTranscripción de referencia esperada para contrastar: \"{expected_transcript}\""

        config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_INSTRUCTION,
            temperature=0.2,
            response_mime_type="application/json",
        )

        logger.info(f"Invoking Gemini ({self.model_name}) for audio {audio_id} ({len(audio_bytes)} bytes)")
        contents_payload: Any = [audio_part, prompt_text]
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents_payload,
            config=config,
        )

        response_text = response.text or "{}"
        try:
            data = json.loads(response_text)
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON response: {response_text}")
            raise ValueError(f"Invalid JSON returned by Gemini: {e}") from e
        import uuid
        eval_id = f"eval_{audio_id}_{uuid.uuid4().hex[:8]}"

        return AudioEvaluation(
            evaluation_id=eval_id,
            audio_id=audio_id,
            audio_sha256=audio_sha256,
            is_reference_audio=is_reference,
            estimated_transcript=data.get("estimated_transcript"),
            perceived_language=data.get("perceived_language", "es-ES"),
            perceived_emotion=data.get("perceived_emotion", "conversacional"),
            secondary_emotions=data.get("secondary_emotions", []),
            expressive_intensity=float(data.get("expressive_intensity", 3.0)),
            intelligibility_score=float(data.get("intelligibility_score", 4.0)),
            prosody_notes=data.get("prosody_notes", ""),
            vocal_characteristics=data.get("vocal_characteristics", ""),
            confidence=float(data.get("confidence", 0.8)),
            explanation=data.get("explanation", ""),
            uncertainties=data.get("uncertainties", []),
            evaluator_provider="google-genai",
            evaluator_model=self.model_name,
            prompt_version=self.PROMPT_VERSION,
        )
