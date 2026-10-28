"""Stage B: Retrieve relevant evidence segments for each claim."""

import json
from pathlib import Path

from ..adapters.base import ModelAdapter
from ..schemas import ExtractedClaim, EvidenceReference, RetrievedSegment

RETRIEVE_PROMPT = """\
You are matching a factual claim from a police incident report to relevant segments of bodycam evidence.

Given the claim below and a transcript of the bodycam footage, identify the most relevant segment(s) of the evidence that relate to this claim. A segment is relevant if it supports, contradicts, or provides context for the claim.

CLAIM:
{claim_text}

CLAIM TYPE: {claim_type}

TRANSCRIPT (timestamped):
{transcript_text}

For each relevant segment, provide:
- start_seconds: when the relevant segment begins
- end_seconds: when it ends
- modality: "audio" if only speech matters, "visual" if only visible action, "both" if both
- transcript_excerpt: the relevant words from the transcript (if audio)

If no relevant evidence exists in the transcript, return an empty segments array.
"""

RETRIEVE_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start_seconds": {"type": "number"},
                    "end_seconds": {"type": "number"},
                    "modality": {"type": "string", "enum": ["audio", "visual", "both"]},
                    "transcript_excerpt": {"type": "string"},
                },
                "required": ["start_seconds", "end_seconds", "modality"],
            },
        },
        "retrieval_status": {
            "type": "string",
            "enum": ["retrieved", "not_retrieved"],
        },
    },
    "required": ["segments", "retrieval_status"],
}


def load_transcript(transcript_path: Path) -> str:
    with open(transcript_path) as f:
        segments = json.load(f)
    lines = []
    for seg in segments:
        m, s = divmod(int(seg["start"]), 60)
        lines.append(f"[{m}:{s:02d}] {seg['text']}")
    return "\n".join(lines)


def retrieve_segments(claim: ExtractedClaim, transcript_path: Path,
                      adapter: ModelAdapter) -> RetrievedSegment:
    transcript_text = load_transcript(transcript_path)
    prompt = RETRIEVE_PROMPT.format(
        claim_text=claim.claim_text,
        claim_type=claim.claim_type or "unknown",
        transcript_text=transcript_text,
    )
    result = adapter.complete_structured(prompt, RETRIEVE_SCHEMA)

    refs = []
    for seg in result.get("segments", []):
        refs.append(EvidenceReference(
            start_seconds=seg["start_seconds"],
            end_seconds=seg["end_seconds"],
            modality=seg.get("modality", "both"),
            transcript_excerpt=seg.get("transcript_excerpt"),
        ))

    return RetrievedSegment(
        claim_id=claim.claim_id,
        evidence_references=refs,
        retrieval_status=result.get("retrieval_status", "not_retrieved" if not refs else "retrieved"),
    )
