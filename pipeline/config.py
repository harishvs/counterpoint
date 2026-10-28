from pathlib import Path

from .schemas import PipelineConfig


def default_config() -> PipelineConfig:
    root = Path(__file__).resolve().parent.parent
    return PipelineConfig(
        model_adapter="claude",
        model_id="claude-sonnet-5-5",
        evidence_dir=root / "benchmark" / "evidence",
        reports_dir=root / "benchmark" / "reports",
        transcript_dir=root / "benchmark" / "raw" / "transcripts",
    )


def make_adapter(config: PipelineConfig):
    if config.model_adapter == "claude":
        from .adapters.claude import ClaudeAdapter
        return ClaudeAdapter(model_name=config.model_id, use_bedrock=config.use_bedrock)
    elif config.model_adapter == "nemotron":
        from .adapters.nemotron import NemotronAdapter
        return NemotronAdapter(
            endpoint=config.nemotron_endpoint,
            model_name=config.model_id,
        )
    elif config.model_adapter == "nemotron-build":
        from .adapters.nemotron_build import NemotronBuildAdapter
        return NemotronBuildAdapter()
    else:
        raise ValueError(f"Unknown adapter: {config.model_adapter}")
