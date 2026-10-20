"""Domain contracts and interfaces (Protocols) for Wheatley Voice Lab."""

from typing import Protocol, runtime_checkable, Optional
from pathlib import Path
from src.voice_lab.domain.models import (
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
)
from src.voice_lab.domain.evaluation_models import AudioEvaluation
from src.voice_lab.domain.generation_models import GenerationRecord


@runtime_checkable
class ReferenceSource(Protocol):
    """Protocol for discovering sections and reference audios from a source."""

    def parse_html(self, html_content: str, base_url: str) -> DiscoveryCatalog:
        """Parse raw HTML and extract the hierarchical catalog."""
        ...


@runtime_checkable
class ReferenceRepository(Protocol):
    """Persistence protocol for reference catalog data."""

    def save_catalog(self, catalog: DiscoveryCatalog) -> None:
        """Persist discovery catalog to storage."""
        ...

    def load_catalog(self) -> Optional[DiscoveryCatalog]:
        """Load persisted discovery catalog if it exists."""
        ...

    def get_audio_by_id(self, audio_id: str) -> Optional[ReferenceAudio]:
        """Retrieve a specific reference audio entry by its stable ID."""
        ...

    def update_audio(self, audio: ReferenceAudio) -> None:
        """Update an audio record in the catalog."""
        ...

    def list_sections(self) -> list[ReferenceSection]:
        """List all discovered sections."""
        ...

    def list_audios(self, section_id: Optional[str] = None) -> list[ReferenceAudio]:
        """List audios, optionally filtered by section."""
        ...


@runtime_checkable
class AudioStorage(Protocol):
    """Protocol for managing reference and generated audio files on disk."""

    def get_reference_path(self, section_path: str, filename: str) -> Path:
        """Compute the deterministic local path for a reference audio file."""
        ...

    def exists(self, path: Path) -> bool:
        """Check if an audio file exists locally."""
        ...


@runtime_checkable
class AudioEvaluator(Protocol):
    """Protocol for evaluating audio expressiveness, transcription, and prosody."""

    def evaluate(
        self,
        audio_path: Path,
        audio_id: str,
        audio_sha256: str,
        is_reference: bool = False,
        expected_transcript: Optional[str] = None,
    ) -> "AudioEvaluation":
        """Evaluate an audio file and return a structured perception report."""
        ...


@runtime_checkable
class SpeechGenerator(Protocol):
    """Protocol for expressive speech generation models (Chatterbox, fallbacks, mocks)."""

    def generate(
        self,
        text: str,
        profile_params: dict[str, float],
        reference_audio_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Synthesize speech audio from text, expressive parameters, and optional audio prompt."""
        ...


@runtime_checkable
class GenerationRepository(Protocol):
    """Persistence protocol for synthetic speech generation experiments."""

    def save_generation(self, record: "GenerationRecord") -> None:
        """Persist a generation metadata record."""
        ...

    def get_generation_by_id(self, generation_id: str) -> Optional["GenerationRecord"]:
        """Retrieve a generation record by its unique ID."""
        ...

    def list_generations(self) -> list["GenerationRecord"]:
        """List all saved generation records in chronological order."""
        ...

    def link_evaluation(self, generation_id: str, evaluation_id: str) -> None:
        """Associate an evaluation ID with a generation record."""
        ...
