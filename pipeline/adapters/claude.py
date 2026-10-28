import base64
import json
import mimetypes
import os
import re
from pathlib import Path

from .base import ModelAdapter

try:
    import anthropic
except ImportError:
    anthropic = None


class ClaudeAdapter(ModelAdapter):
    """Claude adapter supporting both direct API and AWS Bedrock."""

    def __init__(self, model_name: str = "claude-sonnet-5-5",
                 use_bedrock: bool | None = None, region: str = "us-east-1"):
        if anthropic is None:
            raise ImportError("pip install anthropic")

        if use_bedrock is None:
            use_bedrock = not os.environ.get("ANTHROPIC_API_KEY")

        self._use_bedrock = use_bedrock
        if use_bedrock:
            self._client = anthropic.AnthropicBedrock(aws_region=region)
            self._model_name = self._to_bedrock_model_id(model_name)
        else:
            self._client = anthropic.Anthropic()
            self._model_name = model_name

        self._tokens = 0
        self._calls = 0

    @staticmethod
    def _to_bedrock_model_id(model_name: str) -> str:
        """Convert short model names to Bedrock inference profile IDs."""
        mapping = {
            "claude-sonnet-5-5": "us.anthropic.claude-sonnet-5-5",
            "claude-sonnet-5": "us.anthropic.claude-sonnet-5",
            "claude-haiku-5-5": "us.anthropic.claude-haiku-5-5",
            "claude-opus-4-6": "us.anthropic.claude-opus-4-6-v1",
            "claude-sonnet-4-6": "us.anthropic.claude-sonnet-4-6",
            "claude-haiku-4-5": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        }
        if model_name in mapping:
            return mapping[model_name]
        if model_name.startswith("us.") or model_name.startswith("global."):
            return model_name
        return f"us.anthropic.{model_name}"

    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        content = self._build_content(prompt, media)
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=8192,
            messages=[{"role": "user", "content": content}],
        )
        self._calls += 1
        self._tokens += response.usage.input_tokens + response.usage.output_tokens
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

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
