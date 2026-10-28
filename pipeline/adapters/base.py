from abc import ABC, abstractmethod
from pathlib import Path


class ModelAdapter(ABC):
    @abstractmethod
    def complete(self, prompt: str, media: list[Path] | None = None) -> str:
        """Send a prompt (optionally with media files) and return text response."""

    @abstractmethod
    def complete_structured(self, prompt: str, schema: dict,
                            media: list[Path] | None = None) -> dict:
        """Send a prompt and return a structured response matching the schema."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return the model identifier string."""

    @property
    def tokens_used(self) -> int:
        """Return total tokens consumed so far."""
        return 0

    @property
    def api_calls(self) -> int:
        """Return total API calls made so far."""
        return 0
