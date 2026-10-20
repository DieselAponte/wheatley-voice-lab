"""Domain models and manager for expressive emotion profiles."""

import json
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileParameter(BaseModel):
    """Specification of an inference parameter with validated bounds."""

    model_config = ConfigDict(extra="ignore")

    name: str
    default_value: float
    min_value: float
    max_value: float
    description: str

    def validate_value(self, value: float) -> float:
        """Clamp or validate value within allowed boundaries."""
        if value < self.min_value or value > self.max_value:
            raise ValueError(
                f"Parameter '{self.name}' value {value} is out of bounds [{self.min_value}, {self.max_value}]."
            )
        return value


class EmotionProfile(BaseModel):
    """Declarative specification of an expressive speech profile."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(description="Unique profile identifier (e.g. conversacional, nervioso).")
    name: str = Field(description="Display name for UI and reports.")
    description: str = Field(description="Description of the expressive intent.")
    expressive_intent: str = Field(description="Guidance on prosody, tempo, and vocal tone.")
    parameters: dict[str, float] = Field(default_factory=dict, description="Default parameter values.")
    parameter_bounds: dict[str, tuple[float, float]] = Field(
        default_factory=dict, description="Allowed (min, max) limits per parameter."
    )
    recommended_phrases: list[str] = Field(default_factory=list, description="Example test sentences.")
    notes: Optional[str] = None

    def validate_custom_parameters(self, user_params: dict[str, float]) -> dict[str, float]:
        """Validate and merge user-provided parameters against profile bounds."""
        merged = dict(self.parameters)
        for key, val in user_params.items():
            if key in self.parameter_bounds:
                min_v, max_v = self.parameter_bounds[key]
                if val < min_v or val > max_v:
                    raise ValueError(f"Parameter '{key}' with value {val} exceeds bounds [{min_v}, {max_v}].")
            merged[key] = val
        return merged


class ProfileManager:
    """Loads, validates, and resolves declarative emotion profiles."""

    DEFAULT_PROFILES_PATH = Path("configs/emotion_profiles.json")

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_PROFILES_PATH
        self._profiles: dict[str, EmotionProfile] = {}
        self.load_profiles()

    def load_profiles(self) -> None:
        """Load profiles from JSON configuration."""
        if not self.config_path.exists():
            return
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("profiles", []):
            profile = EmotionProfile.model_validate(item)
            self._profiles[profile.id] = profile

    def list_profiles(self) -> list[EmotionProfile]:
        """List all available emotion profiles."""
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[EmotionProfile]:
        """Retrieve profile by ID or return None."""
        return self._profiles.get(profile_id)

    def resolve_profile(self, profile_id: str) -> EmotionProfile:
        """Resolve profile by ID, falling back to 'conversacional' if not found."""
        if profile_id in self._profiles:
            return self._profiles[profile_id]
        if "conversacional" in self._profiles:
            return self._profiles["conversacional"]
        # Fallback default
        return EmotionProfile(
            id="conversacional",
            name="Conversacional",
            description="Tono neutro y estándar de Wheatley.",
            expressive_intent="Entonación estándar y tempo moderado.",
            parameters={"exaggeration": 0.2, "cfg_weight": 0.5, "speed": 1.0, "temperature": 0.6},
            parameter_bounds={"exaggeration": (0.0, 1.0), "cfg_weight": (0.0, 1.5), "speed": (0.5, 2.0), "temperature": (0.1, 1.5)},
        )
