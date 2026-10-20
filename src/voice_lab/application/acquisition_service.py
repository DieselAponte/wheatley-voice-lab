"""Acquisition application service for resilient, controlled audio downloading."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.voice_lab.domain.contracts import ReferenceRepository
from src.voice_lab.domain.models import AcquisitionStatus, ReferenceAudio
from src.voice_lab.infrastructure.audio.storage import LocalAudioStorage
from src.voice_lab.infrastructure.config.settings import settings
from src.voice_lab.infrastructure.wiki.http_client import WikiHttpClient

logger = logging.getLogger(__name__)


class AcquisitionService:
    """Orchestrates controlled reference audio downloads, SHA-256 verification, and catalog persistence."""

    def __init__(
        self,
        repository: ReferenceRepository,
        http_client: Optional[WikiHttpClient] = None,
        storage: Optional[LocalAudioStorage] = None,
    ):
        self.repository = repository
        self.http_client = http_client or WikiHttpClient(
            timeout_seconds=settings.http_timeout_seconds,
            request_delay_seconds=settings.http_request_delay_seconds,
            max_retries=settings.max_retries,
        )
        self.storage = storage or LocalAudioStorage(reference_base_dir=settings.reference_dir)

    def download_audio(
        self,
        audio: ReferenceAudio,
        dry_run: bool = False,
        force: bool = False,
    ) -> ReferenceAudio:
        """Download an individual reference audio clip with verification and state persistence."""
        target_path = self.storage.get_reference_path(audio.section_id, audio.original_filename)

        # Idempotency check: if file already exists and is intact, skip download
        if not force and self.storage.exists(target_path):
            current_sha = self.storage.calculate_sha256(target_path)
            if audio.checksum_sha256 and audio.checksum_sha256 == current_sha:
                logger.debug(f"Audio {audio.id} already downloaded and verified at {target_path}. Skipping.")
                audio.status = AcquisitionStatus.DOWNLOADED
                audio.local_path = str(target_path)
                audio.file_size_bytes = self.storage.get_file_size(target_path)
                return audio

        if dry_run:
            logger.info(f"[DRY-RUN] Would download: {audio.direct_url} -> {target_path}")
            audio.local_path = str(target_path)
            return audio

        logger.info(f"Downloading reference [{audio.id}]: {audio.direct_url} -> {target_path}")
        audio.status = AcquisitionStatus.DOWNLOADING
        self.repository.update_audio(audio)

        try:
            downloaded_file = self.http_client.download_file(
                url=audio.direct_url,
                destination_path=target_path,
                max_bytes=settings.max_download_bytes,
            )

            # Verification: non-empty file and SHA-256 calculation
            file_size = self.storage.get_file_size(downloaded_file)
            if file_size == 0:
                raise ValueError(f"Downloaded file {downloaded_file} is empty (0 bytes).")

            sha256_hash = self.storage.calculate_sha256(downloaded_file)

            # Update audio domain record
            audio.status = AcquisitionStatus.DOWNLOADED
            audio.local_path = str(downloaded_file)
            audio.file_size_bytes = file_size
            audio.checksum_sha256 = sha256_hash
            audio.acquired_at = datetime.now(timezone.utc).isoformat()
            audio.error_message = None

            self.repository.update_audio(audio)
            return audio

        except Exception as exc:
            logger.error(f"Failed to acquire {audio.id} from {audio.direct_url}: {exc}")
            audio.status = AcquisitionStatus.FAILED
            audio.error_message = str(exc)
            self.repository.update_audio(audio)
            return audio

    def acquire_batch(
        self,
        section_id: Optional[str] = None,
        audio_ids: Optional[list[str]] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        retry_failed: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        """Acquire a controlled subset of reference audios."""
        catalog = self.repository.load_catalog()
        if not catalog:
            raise ValueError("Catalog is empty or has not been discovered. Run inspection first.")

        # Candidate selection
        candidates: list[ReferenceAudio] = []
        for audio in catalog.audios:
            if audio_ids and audio.id not in audio_ids:
                continue
            if section_id and not (audio.section_id == section_id or audio.section_id.startswith(f"{section_id}/")):
                continue

            if retry_failed:
                if audio.status == AcquisitionStatus.FAILED:
                    candidates.append(audio)
            else:
                if force or audio.status in (AcquisitionStatus.DISCOVERED, AcquisitionStatus.PENDING_DOWNLOAD):
                    candidates.append(audio)

        if limit is not None and limit > 0:
            candidates = candidates[:limit]

        downloaded = 0
        skipped = 0
        failed = 0
        processed_items: list[ReferenceAudio] = []

        for item in candidates:
            res = self.download_audio(item, dry_run=dry_run, force=force)
            processed_items.append(res)
            if dry_run:
                skipped += 1
            elif res.status == AcquisitionStatus.DOWNLOADED:
                downloaded += 1
            elif res.status == AcquisitionStatus.FAILED:
                failed += 1
            else:
                skipped += 1

        return {
            "total_candidates": len(candidates),
            "dry_run": dry_run,
            "downloaded": downloaded,
            "skipped": skipped,
            "failed": failed,
            "items": processed_items,
        }
