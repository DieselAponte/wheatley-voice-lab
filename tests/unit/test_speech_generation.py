"""Unit tests for expressive emotion profiles and Chatterbox speech adapter."""

import pytest
import soundfile as sf
from pathlib import Path

from src.voice_lab.domain.profiles import EmotionProfile, ProfileManager
from src.voice_lab.infrastructure.models.chatterbox_adapter import ChatterboxAdapter


def test_profile_manager_loads_all_six_profiles():
    manager = ProfileManager(config_path=Path("configs/emotion_profiles.json"))
    profiles = manager.list_profiles()
    assert len(profiles) >= 6

    expected_ids = {"conversacional", "entusiasmado", "confundido", "enfadado", "nervioso", "sarcastico"}
    loaded_ids = {p.id for p in profiles}
    assert expected_ids.issubset(loaded_ids)

    nervioso = manager.get_profile("nervioso")
    assert nervioso is not None
    assert nervioso.parameters["speed"] > 1.2
    assert nervioso.parameter_bounds["exaggeration"] == (0.5, 1.0)


def test_profile_parameter_bounds_validation():
    profile = EmotionProfile(
        id="test_profile",
        name="Test",
        description="Testing bounds",
        expressive_intent="Test intent",
        parameters={"speed": 1.0, "exaggeration": 0.5},
        parameter_bounds={"speed": (0.8, 1.5), "exaggeration": (0.0, 1.0)},
    )

    # Valid parameter
    valid = profile.validate_custom_parameters({"speed": 1.2})
    assert valid["speed"] == 1.2

    # Out of bounds parameter
    with pytest.raises(ValueError) as exc:
        profile.validate_custom_parameters({"speed": 2.5})
    assert "exceeds bounds" in str(exc.value)


def test_profile_manager_fallback_resolution():
    manager = ProfileManager(config_path=Path("configs/emotion_profiles.json"))
    resolved = manager.resolve_profile("non_existent_profile_id")
    assert resolved.id == "conversacional"


def test_chatterbox_adapter_generation(tmp_path):
    adapter = ChatterboxAdapter(sample_rate=24000)
    out_file = tmp_path / "speech_test.wav"

    # Empty text validation
    with pytest.raises(ValueError):
        adapter.generate(text="   ", profile_params={}, output_path=out_file)

    # Valid generation
    result_path = adapter.generate(
        text="¡Hola! Soy Wheatley, encantado de conocerte.",
        profile_params={"speed": 1.1, "exaggeration": 0.7},
        output_path=out_file,
    )

    assert result_path.exists()
    assert result_path == out_file

    info = sf.info(str(result_path))
    assert info.samplerate == 24000
    assert info.channels == 1
    assert info.duration > 0.5
