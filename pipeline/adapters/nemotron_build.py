"""NVIDIA Nemotron Omni via the hosted Build API (integrate.api.nvidia.com).

For development and benchmarking when a local GPU isn't available.
For production/legal use, deploy locally with the NemotronAdapter (vLLM on Spark).

Requires NVIDIA_API_KEY in environment or .env file.
"""

import json
import mimetypes
import os
import re
from pathlib import Path

import requests as http_requests

from .base import ModelAdapter

BUILD_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
BUILD_MODEL_ID = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
MAX_VIDEO_DURATION_SECONDS = 120


class NemotronBuildAdapter(ModelAdapter):

    def __init__(self, api_key: str | None = None,
                 model_name: str = BUILD_MODEL_ID,
                 max_retries: int = 3):
        self._api_key = api_key or self._load_api_key()
        if not self._api_key:
            raise ValueError(
                "NVIDIA_API_KEY not found. Set it in environment or .env file."
            )
        self._model_name = model_name
        self._max_retries = max_retries
        self._tokens = 0
        self._calls = 0

    @staticmethod
    def _load_api_key() -> str | None:
        key = os.environ.get("NVIDIA_API_KEY")
        if key:
            return key
        for env_path in [Path(".env"), Path(__file__).resolve().parent.parent.parent / ".env"]:
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.startswith("NVIDIA_API_KEY="):
                            return line.strip().split("=", 1)[1]
        return None

    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        content = self._build_content(prompt, media)
        payload = {
            "model": self._model_name,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4096,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

        import time
        for attempt in range(self._max_retries):
            response = http_requests.post(BUILD_API_URL, headers=headers, json=payload, timeout=300)
            self._calls += 1

            if response.status_code == 200:
                data = response.json()
                if data.get("usage"):
                    self._tokens += data["usage"].get("prompt_tokens", 0)
                    self._tokens += data["usage"].get("completion_tokens", 0)
                return data["choices"][0]["message"]["content"]

            if response.status_code == 503:
                wait = 5 * (attempt + 1)
                time.sleep(wait)
                continue

            response.raise_for_status()

        raise RuntimeError(f"NVIDIA Build API failed after {self._max_retries} retries (503)")

    def complete_structured(self, prompt: str, schema: dict,
                            media: list[Path] | None = None) -> dict:
        prompt_with_schema = (
            f"{prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            f"Return ONLY the JSON object, no other text."
        )
        text = self.complete(prompt_with_schema, media)
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        if "<think>" in text:
            text = text.split("</think>")[-1].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        text = re.sub(r",\s*([}\]])", r"\1", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    cleaned = re.sub(r",\s*([}\]])", r"\1", match.group())
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass
            return {"error": "json_parse_failed", "raw": text[:200]}

    def _build_content(self, prompt: str, media: list[Path] | None) -> list[dict]:
        """Build content array. Uses public URLs for IA-hosted files, skips local-only."""
        content = []
        for path in (media or []):
            mime = mimetypes.guess_type(str(path))[0] or ""
            url = self._resolve_url(path)
            if not url:
                continue

            if mime.startswith("video/"):
                content.append({"type": "video_url", "video_url": {"url": url}})
            elif mime.startswith("audio/"):
                content.append({"type": "audio_url", "audio_url": {"url": url}})
            elif mime.startswith("image/"):
                content.append({"type": "image_url", "image_url": {"url": url}})

        content.append({"type": "text", "text": prompt})
        return content

    @staticmethod
    def _resolve_url(path: Path) -> str | None:
        """Resolve a local evidence file to a public URL using the manifest.

        The Build API can't access local files — it needs public URLs.
        For IA-hosted videos, we look up the URL from manifest.json.
        """
        manifest_path = path.parent.parent / "manifest.json"
        if not manifest_path.exists():
            return None

        with open(manifest_path) as f:
            manifest = json.load(f)

        for source in manifest.get("sources", []):
            if source.get("file_name") == path.name:
                for url in source.get("urls", []):
                    if "archive.org" in url:
                        return url
                    if "youtube.com" not in url:
                        return url
        return None

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def tokens_used(self) -> int:
        return self._tokens

    @property
    def api_calls(self) -> int:
        return self._calls
