import base64
import json
import mimetypes
from pathlib import Path

from .base import ModelAdapter

try:
    import anthropic
except ImportError:
    anthropic = None


class ClaudeAdapter(ModelAdapter):
    """Claude adapter for development and baseline comparison."""

    def __init__(self, model_name: str = "claude-sonnet-5-5"):
        if anthropic is None:
            raise ImportError("pip install anthropic")
        self._client = anthropic.Anthropic()
        self._model_name = model_name
        self._tokens = 0
        self._calls = 0

    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        content = self._build_content(prompt, media)
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )
        self._calls += 1
        self._tokens += response.usage.input_tokens + response.usage.output_tokens
        return response.content[0].text

    def complete_structured(self, prompt: str, schema: dict,
                            media: list[Path] | None = None) -> dict:
        prompt_with_schema = (
            f"{prompt}\n\n"
            f"Respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            f"Return ONLY the JSON object, no other text."
        )
        text = self.complete(prompt_with_schema, media)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    def _build_content(self, prompt: str, media: list[Path] | None) -> list[dict]:
        content = []
        for path in (media or []):
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            if mime.startswith("image/"):
                data = base64.standard_b64encode(path.read_bytes()).decode()
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": data},
                })
            elif mime == "application/pdf":
                data = base64.standard_b64encode(path.read_bytes()).decode()
                content.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": mime, "data": data},
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
