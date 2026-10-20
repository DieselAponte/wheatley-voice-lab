"""Resilient, polite HTTP client for the Portal Wiki and media assets."""

import logging
import time
from pathlib import Path
from typing import Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class WikiNetworkError(Exception):
    """Raised when network connectivity fails."""


class WikiHTTPError(Exception):
    """Raised when an HTTP response indicates an error."""


class DownloadLimitExceededError(Exception):
    """Raised when a download exceeds the configured maximum size in bytes."""


class WikiHttpClient:
    """Polite and resilient HTTP client for interacting with the wiki and downloading assets."""

    USER_AGENT = (
        "WheatleyVoiceLab/1.0 (+https://github.com/resemble-ai/chatterbox-lab; "
        "Educational and Acoustic Research Bot)"
    )

    def __init__(
        self,
        timeout_seconds: float = 30.0,
        request_delay_seconds: float = 1.5,
        max_retries: int = 3,
        client: Optional[httpx.Client] = None,
    ):
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,audio/*;q=0.8,*/*;q=0.7",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

        self.client = client or httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
        )

    def _apply_rate_limit(self) -> None:
        """Enforce polite pause between consecutive requests."""
        if self.request_delay_seconds <= 0:
            return
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay_seconds:
            sleep_needed = self.request_delay_seconds - elapsed
            logger.debug(f"Applying rate limit delay of {sleep_needed:.2f}s")
            time.sleep(sleep_needed)
        self._last_request_time = time.time()

    def fetch_page(self, url: str) -> str:
        """Fetch page HTML content with retries and rate limiting."""
        self._apply_rate_limit()

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _execute() -> str:
            try:
                response = self.client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP error {exc.response.status_code} fetching {url}")
                raise WikiHTTPError(f"HTTP status {exc.response.status_code} for {url}") from exc
            except httpx.RequestError as exc:
                logger.error(f"Network request error fetching {url}: {exc}")
                raise WikiNetworkError(f"Network failure accessing {url}") from exc

        return _execute()

    def download_file(
        self,
        url: str,
        destination_path: Path,
        max_bytes: int = 25_000_000,
    ) -> Path:
        """Stream download with size checks and atomic write to temporary file."""
        self._apply_rate_limit()
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination_path.with_suffix(f"{destination_path.suffix}.tmp")

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )
        def _execute_download() -> Path:
            try:
                with self.client.stream("GET", url) as response:
                    response.raise_for_status()

                    # Verify Content-Length header if present
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        raise DownloadLimitExceededError(
                            f"Content-Length {content_length} exceeds max allowed {max_bytes} bytes."
                        )

                    total_downloaded = 0
                    with open(temp_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=65536):
                            total_downloaded += len(chunk)
                            if total_downloaded > max_bytes:
                                raise DownloadLimitExceededError(
                                    f"Downloaded {total_downloaded} bytes exceeds limit of {max_bytes} bytes."
                                )
                            f.write(chunk)

                # Atomic replace
                temp_path.replace(destination_path)
                logger.info(f"Successfully downloaded {url} -> {destination_path} ({total_downloaded} bytes)")
                return destination_path
            except (DownloadLimitExceededError, WikiHTTPError, WikiNetworkError):
                if temp_path.exists():
                    temp_path.unlink()
                raise
            except httpx.HTTPStatusError as exc:
                if temp_path.exists():
                    temp_path.unlink()
                raise WikiHTTPError(f"HTTP status {exc.response.status_code} downloading {url}") from exc
            except httpx.RequestError as exc:
                if temp_path.exists():
                    temp_path.unlink()
                raise WikiNetworkError(f"Network error downloading {url}: {exc}") from exc

        return _execute_download()

    def close(self) -> None:
        """Close the underlying HTTP client session."""
        self.client.close()
