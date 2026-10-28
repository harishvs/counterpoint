from pathlib import Path

from .base import ModelAdapter


class NemotronAdapter(ModelAdapter):
    """NVIDIA Nemotron Omni adapter — stub until model access is verified."""

    def __init__(self, endpoint: str = "http://localhost:8000/v1",
                 model_name: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"):
        self._endpoint = endpoint
        self._model_name = model_name
        self._tokens = 0
        self._calls = 0

    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        raise NotImplementedError(
            "Nemotron adapter not yet implemented. "
            "Verify model capabilities and API format first."
        )

    def complete_structured(self, prompt: str, schema: dict,
                            media: list[Path] | None = None) -> dict:
        raise NotImplementedError(
            "Nemotron adapter not yet implemented. "
            "Verify model capabilities and API format first."
        )

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def tokens_used(self) -> int:
        return self._tokens

    @property
    def api_calls(self) -> int:
        return self._calls
