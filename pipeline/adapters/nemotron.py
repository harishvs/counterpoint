"""NVIDIA Nemotron Omni adapter.

Uses OpenAI-compatible API served by vLLM. Supports video, audio, and image inputs.

Video is capped at 2 minutes by the model. The pipeline's retrieve stage should
cut relevant clips before passing to verify.
"""

import json
import mimetypes
import re
from pathlib import Path

from .base import ModelAdapter

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

MAX_VIDEO_DURATION_SECONDS = 120


class NemotronAdapter(ModelAdapter):

    def __init__(self, endpoint: str = "http://localhost:8000/v1",
                 model_name: str = "nvidia/Nemotron-3-Nano-Omni-30B-A3B-Reasoning-NVFP4",
                 enable_thinking: bool = False):
        if OpenAI is None:
            raise ImportError("pip install openai")
        self._client = OpenAI(base_url=endpoint, api_key="not-needed")
        self._model_name = model_name
        self._enable_thinking = enable_thinking
        self._tokens = 0
        self._calls = 0

    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        content = self._build_content(prompt, media)
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "user", "content": content}],
            max_tokens=4096,
            temperature=1.0,
            extra_body={
                "top_k": 1,
                "chat_template_kwargs": {"enable_thinking": self._enable_thinking},
            },
        )
        self._calls += 1
        if response.usage:
            self._tokens += response.usage.prompt_tokens + response.usage.completion_tokens
        text = response.choices[0].message.content or ""
        if self._enable_thinking and "<think>" in text:
            text = text.split("</think>")[-1].strip()
        return text

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
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()
        text = re.sub(r",\s*([}\]])", r"\1", text)
        return json.loads(text)

    def _build_content(self, prompt: str, media: list[Path] | None) -> list[dict]:
        content = []
        for path in (media or []):
            mime = mimetypes.guess_type(str(path))[0] or ""
            file_url = f"file://{path.resolve()}"

            if mime.startswith("video/"):
                content.append({
                    "type": "video_url",
                    "video_url": {"url": file_url},
                })
            elif mime.startswith("audio/"):
                content.append({
                    "type": "audio_url",
                    "audio_url": {"url": file_url},
                })
            elif mime.startswith("image/"):
                content.append({
                    "type": "image_url",
                    "image_url": {"url": file_url},
                })
        content.append({"type": "text", "text": prompt})
        return content

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def tokens_used(self) -> int:
        return self._tokens

    @property
    def api_calls(self) -> int:
        return self._calls
