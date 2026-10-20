"""Unit tests for the Portal Wiki parser."""

from pathlib import Path
from src.voice_lab.infrastructure.wiki.parser import WikiParser, slugify, sanitize_filename


def test_slugify():
    assert slugify("Capítulo 1: Despertares") == "capitulo-1-despertares"
    assert slugify("¡Hola, mundo!") == "hola-mundo"
    assert slugify("  Wheatley  Voice ") == "wheatley-voice"


def test_sanitize_filename():
    assert sanitize_filename("Wheatley: test/sample.wav") == "Wheatley_ test_sample.wav"
    assert sanitize_filename("normal_file.wav") == "normal_file.wav"


def test_parse_sample_wiki_fixture():
    fixture_path = Path("tests/fixtures/sample_wiki.html")
    assert fixture_path.exists(), "Sample wiki fixture must exist."

    html_content = fixture_path.read_text(encoding="utf-8")
    parser = WikiParser()
    catalog = parser.parse_html(html_content, source_url="https://theportalwiki.com/wiki/Wheatley_voice_lines/es")

    assert catalog.source_page.title == "Líneas de voz de Wheatley"
    assert catalog.source_page.total_sections >= 5
    assert catalog.source_page.total_audios >= 6

    # Verify sections hierarchy
    section_titles = [s.title for s in catalog.sections]
    assert "Capítulo 1: Despertares" in section_titles
    assert "Introducción" in section_titles
    assert "Antes de abrir la puerta" in section_titles
    assert "Cámara de pruebas 02" in section_titles
    assert "Capítulo 3: El Regreso" in section_titles

    # Verify audio properties
    first_audio = catalog.audios[0]
    assert first_audio.id.startswith("ref_")
    assert first_audio.original_filename.endswith(".wav")
    assert "i1.theportalwiki.net" in first_audio.direct_url
    assert first_audio.transcript == "¿Hola? ¿Hay alguien allí?"
    assert first_audio.section_id == "capitulo-1-despertares/introduccion/antes-de-abrir-la-puerta"

    # Verify unclassified entries
    assert len(catalog.unclassified_entries) >= 1
    assert "Nota del traductor sin archivo de audio" in catalog.unclassified_entries[0]["text"]
