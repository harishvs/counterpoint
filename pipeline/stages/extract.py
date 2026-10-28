"""Stage A: Extract atomic factual claims from an incident report."""

from pathlib import Path

from ..adapters.base import ModelAdapter
from ..schemas import ExtractedClaim

EXTRACT_PROMPT = """\
You are analyzing a police incident report to extract individual factual claims.

Read the incident report below and extract every distinct factual claim. A factual claim is a statement that can be independently verified against evidence (video, audio, documents).

For each claim, identify:
- claim_text: the exact or close paraphrase of the claim from the report
- report_location: where in the report it appears (e.g. "Narrative, paragraph 2, sentence 1")
- claim_type: one of: spoken_statement, action_description, object_description, temporal_sequence, location_description, identity_description, subjective_characterization

Include ALL verifiable claims: direct quotes, described actions, object descriptions, time references, location details, sequence of events.

INCIDENT REPORT:
{report_text}
"""

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_text": {"type": "string"},
                    "report_location": {"type": "string"},
                    "claim_type": {
                        "type": "string",
                        "enum": [
                            "spoken_statement", "action_description",
                            "object_description", "temporal_sequence",
                            "location_description", "identity_description",
                            "subjective_characterization",
                        ],
                    },
                },
                "required": ["claim_text", "report_location", "claim_type"],
            },
        },
    },
    "required": ["claims"],
}


def extract_claims(report_path: Path, adapter: ModelAdapter) -> list[ExtractedClaim]:
    report_text = report_path.read_text()
    prompt = EXTRACT_PROMPT.format(report_text=report_text)
    result = adapter.complete_structured(prompt, EXTRACT_SCHEMA)

    claims = []
    for i, raw in enumerate(result.get("claims", []), start=1):
        claims.append(ExtractedClaim(
            claim_id=f"cl-{i:03d}",
            claim_text=raw["claim_text"],
            report_location=raw["report_location"],
            claim_type=raw.get("claim_type"),
        ))
    return claims
