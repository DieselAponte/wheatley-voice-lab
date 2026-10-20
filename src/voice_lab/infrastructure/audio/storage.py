"""Audio storage manager for organizing reference files on disk."""

import hashlib
import re
from pathlib import Path
from typing import Optional

from src.voice_lab.domain.contracts import AudioStorage


from src.voice_lab.infrastructure.wiki.parser import sanitize_filename


def sanitize_path_segment(segment: str) -> str:
    """Sanitize directory names for Windows and Unix filesystem safety."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", segment)
    clean = re.sub(r"\s+", "_", clean.strip(". "))
    return clean.lower() or "section"


class LocalAudioStorage(AudioStorage):
    """Manages audio file paths, folder hierarchies, and disk presence."""

    def __init__(self, reference_base_dir: Path = Path("data/references")):
        self.reference_base_dir = reference_base_dir

    def get_reference_path(self, section_id: str, filename: str) -> Path:
        """Construct the hierarchical disk path based on section slug hierarchy."""
        segments = [sanitize_path_segment(part) for part in section_id.split("/") if part.strip()]
        target_dir = self.reference_base_dir
        for seg in segments:
            target_dir = target_dir / seg
        clean_filename = sanitize_filename(filename)
        return target_dir / clean_filename

    def exists(self, path: Path) -> bool:
        """Check if an audio file exists and is not empty."""
        return path.exists() and path.is_file() and path.stat().st_size > 0

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Compute the SHA-256 hash of a local file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def get_file_size(file_path: Path) -> int:
        """Get file size in bytes."""
        return file_path.stat().st_size if file_path.exists() else 0
