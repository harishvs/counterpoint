"""Stage C: Verify each claim against retrieved evidence segments."""

from pathlib import Path

from ..adapters.base import ModelAdapter
from ..schemas import ExtractedClaim, RetrievedSegment, VerifiedClaim, EvidenceReference

VERIFY_PROMPT = """\
You are a fact-checker comparing a claim from a police incident report against bodycam evidence.

CLAIM FROM REPORT:
"{claim_text}"

EVIDENCE TRANSCRIPT SEGMENTS:
{evidence_text}

Compare the claim against the evidence and determine the relationship:
- "supported": The evidence directly supports this claim.
- "potential_conflict": The evidence appears to contradict this claim. Explain specifically what conflicts.
- "ambiguous_or_insufficient": The evidence is unclear, incomplete, or does not directly address this claim.
- "not_assessed": Unable to evaluate (e.g., evidence is purely visual and no video frames available).

Be precise. A conflict requires specific observable evidence that contradicts the claim, not speculation. If the evidence doesn't clearly address the claim, classify as ambiguous_or_insufficient rather than guessing.
"""

VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence_relationship": {
            "type": "string",
            "enum": ["supported", "potential_conflict", "ambiguous_or_insufficient", "not_assessed"],
        },
        "evidence_observations": {
            "type": "string",
            "description": "What specifically was observed in the evidence",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": ["evidence_relationship", "evidence_observations"],
}


def format_evidence(segment: RetrievedSegment) -> str:
    if not segment.evidence_references:
        return "(No evidence segments retrieved)"
    parts = []
    for ref in segment.evidence_references:
        time_str = ""
        if ref.start_seconds is not None and ref.end_seconds is not None:
            m1, s1 = divmod(int(ref.start_seconds), 60)
            m2, s2 = divmod(int(ref.end_seconds), 60)
            time_str = f"[{m1}:{s1:02d}-{m2}:{s2:02d}] "
        text = ref.transcript_excerpt or ref.visual_description or "(no text)"
        parts.append(f"{time_str}{text}")
    return "\n".join(parts)


def verify_claim(claim: ExtractedClaim, segment: RetrievedSegment,
                 adapter: ModelAdapter,
                 video_path: Path | None = None) -> VerifiedClaim:
    evidence_text = format_evidence(segment)

    media = []
    if video_path and video_path.exists():
        media.append(video_path)

    prompt = VERIFY_PROMPT.format(
        claim_text=claim.claim_text,
        evidence_text=evidence_text,
    )
    result = adapter.complete_structured(prompt, VERIFY_SCHEMA, media=media if media else None)

    return VerifiedClaim(
        claim_id=claim.claim_id,
        evidence_relationship=result["evidence_relationship"],
        retrieval_status=segment.retrieval_status,
        evidence_references=segment.evidence_references,
        evidence_observations=result.get("evidence_observations", ""),
        confidence=result.get("confidence"),
    )
