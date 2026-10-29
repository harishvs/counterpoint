"""Stage B: Retrieve relevant evidence segments for each claim.

Two modes:
- keyword search (default): fast, deterministic, no API calls
- llm: uses the model to find segments (slower, less reliable for timestamps)
"""

import json
import re
from pathlib import Path

from ..adapters.base import ModelAdapter
from ..schemas import ExtractedClaim, EvidenceReference, RetrievedSegment

EVENT_KEYWORDS = [
    "stop", "don't move", "dont move", "hands up", "get down", "drop it",
    "get on the ground", "show me your hands", "put your hands",
    "shots fired", "taser", "fire", "shoot", "gun", "weapon", "knife",
    "reverse", "backing", "drive", "vehicle", "car",
    "screaming", "yelling", "running", "fleeing",
    "handcuff", "cuff", "detained", "arrest",
    "paramedic", "ambulance", "medical", "cpr",
    "driver", "passenger", "steering wheel",
    "comply", "resist", "cooperate",
    "reach", "waistband", "pocket",
]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _extract_keywords(claim: ExtractedClaim) -> list[str]:
    keywords = set()
    claim_text = claim.claim_text

    for quoted in re.findall(r'"([^"]*)"', claim_text):
        words = _normalize(quoted).split()
        keywords.update(w for w in words if len(w) > 2)

    claim_lower = claim_text.lower()
    for phrase in EVENT_KEYWORDS:
        if phrase in claim_lower:
            keywords.update(phrase.split())

    words = _normalize(claim_text).split()
    keywords.update(w for w in words if len(w) > 5)

    stopwords = {"the", "that", "this", "with", "from", "were", "been",
                 "have", "being", "which", "their", "there", "about",
                 "would", "could", "should", "into", "also", "officer",
                 "officers", "subject", "stated", "observed", "approximately",
                 "report", "vehicle"}
    return list(keywords - stopwords)


def load_transcript_segments(transcript_path: Path) -> list[dict]:
    with open(transcript_path) as f:
        return json.load(f)


def load_transcript(transcript_path: Path) -> str:
    segments = load_transcript_segments(transcript_path)
    lines = []
    for seg in segments:
        m, s = divmod(int(seg["start"]), 60)
        lines.append(f"[{m}:{s:02d}] {seg['text']}")
    return "\n".join(lines)


def retrieve_by_keyword(claim: ExtractedClaim,
                        transcript_path: Path,
                        context_window: int = 3) -> RetrievedSegment:
    """Fast keyword-based retrieval — no API calls."""
    segments = load_transcript_segments(transcript_path)
    if not segments:
        return RetrievedSegment(claim_id=claim.claim_id, retrieval_status="not_retrieved")

    keywords = _extract_keywords(claim)
    if not keywords:
        return RetrievedSegment(claim_id=claim.claim_id, retrieval_status="not_retrieved")

    best_score = 0
    best_idx = None

    for i in range(len(segments)):
        end = min(i + 3, len(segments))
        window_text = " ".join(_normalize(s["text"]) for s in segments[i:end])
        score = 0
        for kw in keywords:
            if kw in window_text:
                score += 1
                if len(kw) > 5:
                    score += 0.5
        if score > best_score:
            best_score = score
            best_idx = i

    if best_idx is None or best_score < 1:
        return RetrievedSegment(claim_id=claim.claim_id, retrieval_status="not_retrieved")

    start_idx = max(0, best_idx - context_window)
    end_idx = min(len(segments) - 1, best_idx + context_window + 2)

    start_sec = segments[start_idx]["start"]
    end_sec = segments[end_idx]["end"]
    excerpt = " ".join(s["text"] for s in segments[start_idx:end_idx + 1])

    ref = EvidenceReference(
        start_seconds=round(start_sec, 1),
        end_seconds=round(end_sec, 1),
        modality="both",
        transcript_excerpt=excerpt[:300],
    )

    return RetrievedSegment(
        claim_id=claim.claim_id,
        evidence_references=[ref],
        retrieval_status="retrieved",
    )


def retrieve_by_llm(claim: ExtractedClaim, transcript_path: Path,
                    adapter: ModelAdapter) -> RetrievedSegment:
    """LLM-based retrieval — uses model to find relevant segments."""
    transcript_text = load_transcript(transcript_path)

    prompt = (
        "You are matching a factual claim from a police incident report to relevant "
        "segments of bodycam evidence.\n\n"
        f"CLAIM:\n{claim.claim_text}\n\n"
        f"CLAIM TYPE: {claim.claim_type or 'unknown'}\n\n"
        f"TRANSCRIPT (timestamped):\n{transcript_text}\n\n"
        "For each relevant segment, provide:\n"
        "- start_seconds: when the relevant segment begins\n"
        "- end_seconds: when it ends\n"
        "- modality: \"audio\" if only speech matters, \"visual\" if only visible action, \"both\"\n"
        "- transcript_excerpt: the relevant words from the transcript\n\n"
        "If no relevant evidence exists, return an empty segments array."
    )

    schema = {
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

    result = adapter.complete_structured(prompt, schema)

    if "error" in result:
        return RetrievedSegment(claim_id=claim.claim_id, retrieval_status="failed")

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


def retrieve_segments(claim: ExtractedClaim, transcript_path: Path,
                      adapter: ModelAdapter, method: str = "keyword") -> RetrievedSegment:
    if method == "keyword":
        return retrieve_by_keyword(claim, transcript_path)
    return retrieve_by_llm(claim, transcript_path, adapter)
