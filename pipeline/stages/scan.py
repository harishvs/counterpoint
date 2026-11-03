"""Video scanning: verify claims by scanning 2-minute video chunks.

Instead of per-claim retrieval, segments the video into chunks and asks
the model to evaluate all claims against each chunk. This gives visual
claims a chance to be verified even when there's no transcript match.
"""

import json
import subprocess
from pathlib import Path

from ..adapters.base import ModelAdapter
from ..schemas import ExtractedClaim, VerifiedClaim, EvidenceReference

CHUNK_DURATION = 110  # seconds (under 2-min limit with margin)
CHUNK_OVERLAP = 10    # seconds overlap between chunks

SCAN_PROMPT = """\
You are a fact-checker reviewing bodycam footage against claims from a police incident report.

The attached video clip covers seconds {start_s}-{end_s} of the bodycam recording.

TRANSCRIPT FOR THIS SEGMENT:
{transcript_segment}

CLAIMS TO EVALUATE:
{claims_text}

For each claim, watch the video carefully and determine:
- "supported": You can see or hear evidence that directly supports this claim.
- "potential_conflict": You can see or hear evidence that contradicts this claim. Describe what conflicts.
- "ambiguous_or_insufficient": The clip doesn't clearly show or say anything about this claim.

Only evaluate claims where you have actual visual or audio evidence from THIS clip. If a claim refers to events not shown in this clip, mark it "ambiguous_or_insufficient".

Be decisive: if you can see that the subject is in the driver's seat, and the claim says passenger seat, that is a "potential_conflict", not "ambiguous_or_insufficient".
"""

SCAN_SCHEMA = {
    "type": "object",
    "properties": {
        "evaluations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_number": {"type": "integer"},
                    "evidence_relationship": {
                        "type": "string",
                        "enum": ["supported", "potential_conflict", "ambiguous_or_insufficient"],
                    },
                    "evidence_observations": {"type": "string"},
                },
                "required": ["claim_number", "evidence_relationship"],
            },
        },
    },
    "required": ["evaluations"],
}


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0.0


def extract_chunk(video_path: Path, start: float, duration: float,
                  output_dir: Path) -> Path | None:
    """Extract a video chunk using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_name = f"{video_path.stem}_chunk_{int(start)}_{int(start + duration)}.mp4"
    chunk_path = output_dir / chunk_name

    if chunk_path.exists():
        return chunk_path

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(start), "-i", str(video_path),
             "-t", str(duration), "-c:v", "libx264", "-preset", "fast",
             "-c:a", "aac", "-loglevel", "error", str(chunk_path)],
            capture_output=True, timeout=120, check=True,
        )
        return chunk_path
    except Exception:
        chunk_path.unlink(missing_ok=True)
        return None


def get_transcript_segment(transcript_path: Path | None,
                           start: float, end: float) -> str:
    """Get transcript text for a time window."""
    if not transcript_path or not transcript_path.exists():
        return "(No transcript available)"
    with open(transcript_path) as f:
        segments = json.load(f)
    lines = []
    for seg in segments:
        if seg["end"] >= start and seg["start"] <= end:
            m, s = divmod(int(seg["start"]), 60)
            lines.append(f"[{m}:{s:02d}] {seg['text']}")
    return "\n".join(lines) if lines else "(No speech in this segment)"


def format_claims_for_scan(claims: list[ExtractedClaim]) -> str:
    """Format claims as a numbered list for the scan prompt."""
    lines = []
    for i, claim in enumerate(claims):
        lines.append(f"{i + 1}. \"{claim.claim_text}\"")
    return "\n".join(lines)


def scan_video(claims: list[ExtractedClaim], video_path: Path,
               transcript_path: Path | None, adapter: ModelAdapter,
               chunk_dir: Path) -> list[VerifiedClaim]:
    """Scan video in chunks, evaluating all claims against each chunk.

    Returns the best (most decisive) result for each claim across all chunks.
    """
    duration = get_video_duration(video_path)
    if duration <= 0:
        return [VerifiedClaim(
            claim_id=c.claim_id, claim_text=c.claim_text,
            evidence_relationship="not_assessed",
            evidence_observations="Could not read video duration",
        ) for c in claims]

    # Build chunk boundaries
    chunks = []
    start = 0.0
    while start < duration:
        end = min(start + CHUNK_DURATION, duration)
        chunks.append((start, end))
        start += CHUNK_DURATION - CHUNK_OVERLAP
    print(f"    Video: {duration:.0f}s, {len(chunks)} chunks of ~{CHUNK_DURATION}s")

    # Track best result per claim
    best = {}
    for claim in claims:
        best[claim.claim_id] = VerifiedClaim(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            evidence_relationship="ambiguous_or_insufficient",
            retrieval_status="not_retrieved",
            evidence_observations="",
        )

    claims_text = format_claims_for_scan(claims)

    for chunk_idx, (chunk_start, chunk_end) in enumerate(chunks):
        chunk_path = extract_chunk(video_path, chunk_start,
                                   chunk_end - chunk_start, chunk_dir)
        if not chunk_path:
            print(f"    Chunk {chunk_idx + 1}/{len(chunks)}: ffmpeg failed, skipping")
            continue

        transcript_seg = get_transcript_segment(
            transcript_path, chunk_start, chunk_end)

        prompt = SCAN_PROMPT.format(
            start_s=int(chunk_start),
            end_s=int(chunk_end),
            transcript_segment=transcript_seg,
            claims_text=claims_text,
        )

        print(f"    Chunk {chunk_idx + 1}/{len(chunks)} [{int(chunk_start)}s-{int(chunk_end)}s]...", end="", flush=True)

        try:
            result = adapter.complete_structured(
                prompt, SCAN_SCHEMA, media=[chunk_path])
        except Exception as e:
            print(f" error: {str(e)[:80]}")
            continue

        if "error" in result:
            print(f" parse error")
            continue

        evals = result.get("evaluations", [])
        conflicts = sum(1 for e in evals if e.get("evidence_relationship") == "potential_conflict")
        supported = sum(1 for e in evals if e.get("evidence_relationship") == "supported")
        print(f" {conflicts} conflicts, {supported} supported, {len(evals)} total")

        for ev in evals:
            num = ev.get("claim_number", 0)
            if num < 1 or num > len(claims):
                continue
            claim = claims[num - 1]
            rel = ev.get("evidence_relationship", "ambiguous_or_insufficient")
            obs = ev.get("evidence_observations", "")

            current = best[claim.claim_id]
            # Upgrade: conflict > supported > ambiguous
            priority = {"potential_conflict": 3, "supported": 2,
                        "ambiguous_or_insufficient": 1, "not_assessed": 0}
            if priority.get(rel, 0) > priority.get(current.evidence_relationship, 0):
                best[claim.claim_id] = VerifiedClaim(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    evidence_relationship=rel,
                    retrieval_status="retrieved",
                    evidence_references=[EvidenceReference(
                        start_seconds=chunk_start,
                        end_seconds=chunk_end,
                        modality="both",
                    )],
                    evidence_observations=obs,
                )

    return [best[c.claim_id] for c in claims]
