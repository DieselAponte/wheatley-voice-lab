"""HTML parser for extracting hierarchical sections and voice lines from Portal Wiki."""

import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional, Any
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup, Tag

from src.voice_lab.domain.models import (
    AcquisitionStatus,
    AssetProvenance,
    DiscoveryCatalog,
    ReferenceAudio,
    ReferenceSection,
    SourcePage,
    VerificationStatus,
)


def slugify(text: str) -> str:
    """Produce a safe, deterministic ASCII slug from arbitrary text."""
    text = unquote(text)
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Replace underscores with spaces before cleaning
    text = text.replace("_", " ")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and remove invalid OS characters."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    clean = clean.strip(". ")
    return clean or "audio_file.wav"


class WikiParser:
    """Parser for Portal Wiki Wheatley voice lines page."""

    AUDIO_EXTENSIONS = (".wav", ".mp3", ".ogg", ".flac")

    def __init__(self, base_wiki_url: str = "https://theportalwiki.com"):
        self.base_wiki_url = base_wiki_url

    def parse_html(self, html_content: str, source_url: str) -> DiscoveryCatalog:
        """Parse the full HTML and extract sections, audios, and metadata."""
        soup = BeautifulSoup(html_content, "html.parser")
        title_el = soup.find("h1", id="firstHeading")
        page_title = title_el.get_text(strip=True) if title_el else "Líneas de voz de Wheatley"

        sections = self._parse_table_of_contents(soup)
        audios, unclassified = self._extract_audio_entries(soup, sections, source_url)

        source_page = SourcePage(
            url=source_url,
            title=page_title,
            inspected_at=datetime.now(timezone.utc).isoformat(),
            total_sections=len(sections),
            total_audios=len(audios),
        )

        return DiscoveryCatalog(
            source_page=source_page,
            sections=sections,
            audios=audios,
            unclassified_entries=unclassified,
        )

    def _parse_table_of_contents(self, soup: BeautifulSoup) -> list[ReferenceSection]:
        """Extract the hierarchical tree of chapters and sub-sections from #toc."""
        toc_div = soup.find(id="toc")
        if not toc_div:
            return []

        sections: list[ReferenceSection] = []
        root_ul = toc_div.find("ul")
        if not root_ul or not isinstance(root_ul, Tag):
            return []

        def _walk_toc(ul: Tag, parent: Optional[ReferenceSection] = None, level: int = 1):
            for li in ul.find_all("li", recursive=False):
                a_tag = li.find("a", href=True)
                if not a_tag:
                    continue

                href = a_tag["href"]
                anchor = href.lstrip("#")
                toctext_span = a_tag.find("span", class_="toctext")
                title = toctext_span.get_text(strip=True) if toctext_span else a_tag.get_text(strip=True)

                slug = slugify(anchor or title)
                sec_id = f"{parent.id}/{slug}" if parent else slug
                full_path = f"{parent.full_path} > {title}" if parent else title

                section = ReferenceSection(
                    id=sec_id,
                    title=title,
                    level=level,
                    order_index=len(sections),
                    parent_id=parent.id if parent else None,
                    anchor=anchor,
                    full_path=full_path,
                )
                sections.append(section)

                # Check for nested sub-sections
                child_ul = li.find("ul", recursive=False)
                if child_ul and isinstance(child_ul, Tag):
                    _walk_toc(child_ul, parent=section, level=level + 1)

        _walk_toc(root_ul)
        return sections

    def _extract_audio_entries(
        self,
        soup: BeautifulSoup,
        sections: list[ReferenceSection],
        source_url: str,
    ) -> tuple[list[ReferenceAudio], list[dict[str, Any]]]:
        """Traverse the content elements, map them to current active section, and extract audio clips."""
        body = soup.find(id="bodyContent") or soup.find(class_="mw-parser-output") or soup
        audios: list[ReferenceAudio] = []
        unclassified: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        # Build map of anchor/title -> section for fast heading lookup
        anchor_to_section: dict[str, ReferenceSection] = {}
        title_to_section: dict[str, ReferenceSection] = {}
        for sec in sections:
            if sec.anchor:
                anchor_to_section[sec.anchor.lower()] = sec
                anchor_to_section[slugify(sec.anchor)] = sec
            anchor_to_section[sec.id] = sec
            title_to_section[sec.title.lower()] = sec
            title_to_section[slugify(sec.title)] = sec

        current_section = sections[0] if sections else ReferenceSection(
            id="general",
            title="General",
            level=1,
            order_index=0,
            full_path="General",
        )
        section_order_counters: dict[str, int] = {}

        # Look for headings and list items in document order
        for el in body.find_all(["h2", "h3", "h4", "h5", "ul"]):
            if el.find_parent(id="toc") or el.find_parent(class_="toc"):
                continue

            if el.name in ["h2", "h3", "h4", "h5"]:
                # Check for heading anchor or text matching known sections
                span_anchor = el.find("span", id=True)
                anchor_id = span_anchor["id"] if span_anchor else el.get("id", "")
                heading_text = el.get_text(strip=True)

                candidate = (
                    anchor_to_section.get(anchor_id.lower())
                    or anchor_to_section.get(slugify(anchor_id))
                    or title_to_section.get(heading_text.lower())
                    or title_to_section.get(slugify(heading_text))
                )
                if candidate:
                    current_section = candidate
            elif el.name == "ul":
                # Find all audio links inside list items
                # We iterate directly over li items
                for li in el.find_all("li"):
                    links = li.find_all("a", href=True)
                    audio_links = [
                        a for a in links
                        if any(a["href"].lower().endswith(ext) for ext in self.AUDIO_EXTENSIONS)
                        or ("class" in a.attrs and "internal" in a["class"])
                    ]

                    if not audio_links:
                        # Non-audio item, record if it has dialogue text
                        text = li.get_text(strip=True)
                        if text and len(text) > 3 and not li.find("ul"):
                            unclassified.append({
                                "text": text,
                                "section_id": current_section.id,
                                "section_path": current_section.full_path,
                                "reason": "No audio link found in list item",
                            })
                        continue

                    for a in audio_links:
                        href = a["href"]
                        # Resolve full URL
                        direct_url = href
                        if direct_url.startswith("//"):
                            direct_url = "https:" + direct_url
                        elif direct_url.startswith("/"):
                            direct_url = urljoin(self.base_wiki_url, direct_url)

                        if direct_url in seen_urls:
                            continue
                        seen_urls.add(direct_url)

                        # Extract filename and format
                        raw_filename = direct_url.split("/")[-1].split("?")[0]
                        filename = sanitize_filename(unquote(raw_filename))
                        fmt = filename.split(".")[-1].lower() if "." in filename else "wav"

                        # Extract transcript from link text or title attribute
                        transcript = a.get_text(strip=True)
                        if not transcript:
                            transcript = a.get("title", "")
                        # Clean quotes around dialogue
                        transcript = transcript.strip('"\u201c\u201d\u00ab\u00bb')

                        # Stable audio ID
                        stem = filename.rsplit(".", 1)[0]
                        audio_id = f"ref_{slugify(stem)}"

                        order_idx = section_order_counters.get(current_section.id, 0)
                        section_order_counters[current_section.id] = order_idx + 1

                        file_page_url = f"{self.base_wiki_url}/wiki/File:{filename}"
                        provenance = AssetProvenance(
                            source_page_url=source_url,
                            file_page_url=file_page_url,
                            direct_audio_url=direct_url,
                            license_info="Portal 2 / Valve Corporation proprietary assets.",
                            verification_status=VerificationStatus.VERIFIED_VALVE_PROPRIETARY,
                        )

                        audio = ReferenceAudio(
                            id=audio_id,
                            original_filename=filename,
                            direct_url=direct_url,
                            file_page_url=file_page_url,
                            transcript=transcript,
                            section_id=current_section.id,
                            section_path=current_section.full_path,
                            order_in_section=order_idx,
                            expected_format=fmt,
                            status=AcquisitionStatus.DISCOVERED,
                            provenance=provenance,
                        )
                        audios.append(audio)

        return audios, unclassified
