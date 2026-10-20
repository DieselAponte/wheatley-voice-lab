"""Domain models for Wheatley Voice Lab using Pydantic v2."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class AcquisitionStatus(str, Enum):
    """Lifecycle status of a reference audio asset."""

    DISCOVERED = "DISCOVERED"
    PENDING_DOWNLOAD = "PENDING_DOWNLOAD"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"
    INVALID = "INVALID"


class VerificationStatus(str, Enum):
    """Legal rights and provenance verification state."""

    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED_VALVE_PROPRIETARY = "VERIFIED_VALVE_PROPRIETARY"
    VERIFIED_PUBLIC_DOMAIN = "VERIFIED_PUBLIC_DOMAIN"
    UNKNOWN = "UNKNOWN"


class AssetProvenance(BaseModel):
    """Provenance tracking and legal rights verification metadata."""

    model_config = ConfigDict(extra="ignore")

    source_page_url: str
    file_page_url: Optional[str] = None
    direct_audio_url: str
    license_info: str = "Portal 2 / Valve Corporation proprietary dialogue assets."
    verification_status: VerificationStatus = VerificationStatus.VERIFIED_VALVE_PROPRIETARY
    notes: Optional[str] = (
        "Non-commercial experimental research and speech synthesis evaluation."
    )


class ReferenceSection(BaseModel):
    """Hierarchical section or chapter discovered in the voice lines page."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique, stable slug for the section hierarchy.")
    title: str = Field(description="Visible human-readable section title.")
    level: int = Field(ge=1, le=6, description="Heading level (1=Chapter, 2=Subchapter, etc.)")
    order_index: int = Field(ge=0, description="Sequential order in the document.")
    parent_id: Optional[str] = Field(default=None, description="Parent section ID if nested.")
    anchor: Optional[str] = Field(default=None, description="HTML anchor tag.")
    full_path: str = Field(description="Human-readable section breadcrumb trail.")


class ReferenceAudio(BaseModel):
    """Catalog entry for an acquired or discoverable reference audio clip."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Stable internal identifier (e.g. ref_wheatley_openinghello01_es).")
    original_filename: str = Field(description="Raw filename from the wiki storage.")
    direct_url: str = Field(description="Direct URL to fetch the audio file.")
    file_page_url: Optional[str] = Field(default=None, description="Documentation page of the file.")
    transcript: Optional[str] = Field(default=None, description="Dialogue line in Spanish.")
    section_id: str = Field(description="ID of the associated ReferenceSection.")
    section_path: str = Field(description="Breadcrumbs of the section.")
    order_in_section: int = Field(ge=0, description="Index within the section.")
    expected_format: str = Field(default="wav", description="Expected audio extension/container.")
    status: AcquisitionStatus = Field(default=AcquisitionStatus.DISCOVERED)
    provenance: AssetProvenance

    # Technical metadata (populated upon download and inspection)
    local_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    duration_seconds: Optional[float] = None
    sample_rate_hz: Optional[int] = None
    channels: Optional[int] = None
    acquired_at: Optional[str] = None
    error_message: Optional[str] = None


class SourcePage(BaseModel):
    """Metadata describing the indexed source page."""

    model_config = ConfigDict(extra="ignore")

    url: str
    title: str
    inspected_at: str
    total_sections: int = 0
    total_audios: int = 0
    schema_version: str = "1.0.0"


class DiscoveryCatalog(BaseModel):
    """Complete discovery manifest containing discovered sections and references."""

    model_config = ConfigDict(extra="ignore")

    source_page: SourcePage
    sections: list[ReferenceSection] = Field(default_factory=list)
    audios: list[ReferenceAudio] = Field(default_factory=list)
    unclassified_entries: list[dict[str, Any]] = Field(default_factory=list)
