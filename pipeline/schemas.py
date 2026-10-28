from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvidenceReference:
    start_seconds: float | None = None
    end_seconds: float | None = None
    modality: str = "both"
    transcript_excerpt: str | None = None
    visual_description: str | None = None


@dataclass
class ExtractedClaim:
    claim_id: str
    claim_text: str
    report_location: str
    claim_type: str | None = None


@dataclass
class RetrievedSegment:
    claim_id: str
    evidence_references: list[EvidenceReference] = field(default_factory=list)
    retrieval_status: str = "retrieved"


@dataclass
class VerifiedClaim:
    claim_id: str
    evidence_relationship: str  # supported | potential_conflict | ambiguous_or_insufficient | not_assessed
    claim_text: str = ""
    retrieval_status: str = "retrieved"
    evidence_references: list[EvidenceReference] = field(default_factory=list)
    evidence_observations: str = ""
    confidence: float | None = None


@dataclass
class PipelineConfig:
    model_adapter: str = "claude"
    model_id: str = "claude-haiku-5-5"
    use_bedrock: bool = True
    nemotron_endpoint: str = "http://localhost:8000/v1"
    evidence_dir: Path = Path("benchmark/evidence")
    reports_dir: Path = Path("benchmark/reports")
    max_frames: int = 50
    frame_interval_seconds: float = 10.0
    transcript_dir: Path | None = None


@dataclass
class ScenarioPrediction:
    scenario_id: str
    model: str
    pipeline: str
    claims: list[VerifiedClaim] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    total_tokens: int = 0
    total_api_calls: int = 0

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "model": self.model,
            "pipeline": self.pipeline,
            "processing_time_seconds": self.processing_time_seconds,
            "total_tokens": self.total_tokens,
            "total_api_calls": self.total_api_calls,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text,
                    "evidence_relationship": c.evidence_relationship,
                    "retrieval_status": c.retrieval_status,
                    "evidence_references": [
                        {"start_seconds": r.start_seconds, "end_seconds": r.end_seconds}
                        for r in c.evidence_references
                        if r.start_seconds is not None
                    ],
                    "evidence_observations": c.evidence_observations,
                    **({"confidence": c.confidence} if c.confidence is not None else {}),
                }
                for c in self.claims
            ],
        }
