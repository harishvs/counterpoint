"""Scan bodycam video with swiftpick, a decision model: every claim is a typed choice question.

swiftpick-30B-A3B (served by `strands-decider serve --multimodal`) answers fixed-option
questions about one state with calibrated probabilities instead of generating text. One
request carries a short chunk of video, its audio and its transcript, and every claim of
the report as its own question; the server encodes the chunk once and reads each claim off
a shared prefix. The model reads at most 16 frames per request, so chunks are short
(20 s by default: under one frame a second is lost).

Each chunk's probabilities are kept (`scan` returns them all), so the rule that turns them
into one verdict per claim, and its thresholds, can be chosen afterwards without asking the
model again (`aggregate`).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from ..schemas import EvidenceReference, ExtractedClaim, VerifiedClaim
from .scan import get_transcript_segment, get_video_duration

LABELS = {
    "supported": "the footage or what is said in it directly supports the claim",
    "potential_conflict": "the footage or what is said in it contradicts the claim",
    "ambiguous_or_insufficient": "this segment does not show or address what the claim describes",
}
CHUNK_SECONDS = 20.0
STRIDE_SECONDS = 15.0  # 5 s overlap, so an event on a boundary is seen whole once
FRAME_HEIGHT = 540  # the model resizes each frame to ~1,024 16-px patches (about 680x384)


class SwiftpickClient:
    """POSTs typed questions to a strands-decider server's /v1/systemone."""

    def __init__(self, endpoint: str = "http://localhost:8000", timeout: float = 300.0):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.calls = 0
        self.tokens = 0

    def health(self) -> dict:
        with urllib.request.urlopen(f"{self.endpoint}/health", timeout=30) as r:
            return json.load(r)

    def ask(self, state: str, questions: dict, videos: list[bytes] = (),
            audio: list[bytes] = ()) -> dict:
        body = {"state": state, "questions": questions}
        if videos:
            body["videos"] = [base64.b64encode(v).decode() for v in videos]
        if audio:
            body["audio"] = [base64.b64encode(a).decode() for a in audio]
        req = urllib.request.Request(
            f"{self.endpoint}/v1/systemone", data=json.dumps(body).encode(),
            headers={"content-type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                out = json.load(r)
        except urllib.error.HTTPError as e:  # 422: refused (too long, unreadable media)
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}") from e
        self.calls += 1
        self.tokens += out.get("usage", {}).get("input_tokens", 0)
        return out


def chunk_bounds(duration: float, length: float = CHUNK_SECONDS,
                 stride: float = STRIDE_SECONDS) -> list[tuple[float, float]]:
    bounds, start = [], 0.0
    while start < duration:
        bounds.append((start, min(start + length, duration)))
        if start + length >= duration:
            break
        start += stride
    return bounds


def cut_chunk(video: Path, start: float, end: float, out_dir: Path,
              with_audio: bool) -> tuple[Path | None, Path | None]:
    """(silent mp4 at FRAME_HEIGHT, 16 kHz mono wav or None) for [start, end)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{video.stem}_{start:.0f}_{end:.0f}"
    mp4, wav = out_dir / f"{stem}.mp4", out_dir / f"{stem}.wav"
    run = lambda *args: subprocess.run(  # noqa: E731
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(video),
         "-t", f"{end - start:.3f}", *args], capture_output=True, timeout=180)
    # Written to a private name, then renamed: shards that share a video cut the same chunks.
    tmp = out_dir / f".{stem}.{os.getpid()}"
    if not mp4.exists():
        r = run("-an", "-vf", f"scale=-2:{FRAME_HEIGHT}", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "23", "-f", "mp4", f"{tmp}.mp4")
        if r.returncode:
            Path(f"{tmp}.mp4").unlink(missing_ok=True)
            return None, None
        os.replace(f"{tmp}.mp4", mp4)
    if with_audio and not wav.exists() and not (out_dir / f"{stem}.noaudio").exists():
        r = run("-vn", "-ac", "1", "-ar", "16000", "-f", "wav", f"{tmp}.wav")
        size = Path(f"{tmp}.wav").stat().st_size if Path(f"{tmp}.wav").exists() else 0
        if r.returncode or size < 3200 + 44:  # no audio track, or under 0.1 s
            Path(f"{tmp}.wav").unlink(missing_ok=True)
            (out_dir / f"{stem}.noaudio").touch()
        else:
            os.replace(f"{tmp}.wav", wav)
    return mp4, (wav if with_audio and wav.exists() else None)


def _questions(claims: list[ExtractedClaim]) -> dict:
    return {
        c.claim_id: {
            "type": "choice",
            "instructions": (f'A claim from the police incident report: "{c.claim_text}" '
                             "How does this bodycam segment relate to the claim?"),
            "criteria": LABELS,
        }
        for c in claims
    }


def scan(claims: list[ExtractedClaim], video: Path, transcript: Path | None,
         client: SwiftpickClient, chunk_dir: Path, length: float = CHUNK_SECONDS,
         stride: float = STRIDE_SECONDS, with_audio: bool = True,
         with_video: bool = True) -> dict:
    """Ask every claim of every chunk; returns the raw per-chunk probabilities."""
    duration = get_video_duration(video)
    chunks = []
    questions = _questions(claims)
    bounds = chunk_bounds(duration, length, stride) if duration > 0 else []
    print(f"    Video: {duration:.0f}s, {len(bounds)} chunks of {length:.0f}s, "
          f"{len(claims)} claims each")
    for i, (start, end) in enumerate(bounds):
        mp4, wav = cut_chunk(video, start, end, chunk_dir, with_audio)
        entry = {"start": start, "end": end, "audio": wav is not None}
        if mp4 is None:
            entry["error"] = "ffmpeg failed"
            chunks.append(entry)
            continue
        m1, s1 = divmod(int(start), 60)
        m2, s2 = divmod(int(end), 60)
        state = (f"Bodycam footage, {m1}:{s1:02d} to {m2}:{s2:02d} of the recording.\n"
                 f"Transcript of this segment:\n"
                 f"{get_transcript_segment(transcript, start, end)}")
        try:
            out = client.ask(state, questions, videos=[mp4.read_bytes()] if with_video else [],
                             audio=[wav.read_bytes()] if wav else [])
            entry["probs"] = {cid: a["probabilities"] for cid, a in out["answers"].items()}
        except Exception as e:  # recorded, not fatal: the claim keeps its other chunks
            entry["error"] = str(e)[:300]
        chunks.append(entry)
        if (i + 1) % 10 == 0 or i + 1 == len(bounds):
            print(f"    chunk {i + 1}/{len(bounds)}", flush=True)
    return {
        "video": video.name, "duration": duration, "chunk_seconds": length,
        "stride_seconds": stride, "with_audio": with_audio, "with_video": with_video,
        "claims": [{"claim_id": c.claim_id, "claim_text": c.claim_text} for c in claims],
        "chunks": chunks,
    }


def aggregate(raw: dict, conflict_threshold: float = 0.5,
              support_threshold: float = 0.5) -> list[VerifiedClaim]:
    """One verdict per claim: its highest P(conflict) over the chunks, flagged at
    `conflict_threshold`; otherwise supported when some chunk's P(supported) reaches
    `support_threshold`; otherwise ambiguous. The cited segment is the chunk that decided."""
    out = []
    ok = [c for c in raw["chunks"] if "probs" in c]
    for claim in raw["claims"]:
        cid = claim["claim_id"]
        rows = [(c, c["probs"][cid]) for c in ok if cid in c["probs"]]
        if not rows:
            out.append(VerifiedClaim(claim_id=cid, claim_text=claim["claim_text"],
                                     evidence_relationship="not_assessed",
                                     retrieval_status="not_retrieved"))
            continue
        conf_chunk, conf_p = max(rows, key=lambda r: r[1]["potential_conflict"])
        sup_chunk, sup_p = max(rows, key=lambda r: r[1]["supported"])
        if conf_p["potential_conflict"] >= conflict_threshold:
            rel, chunk, p = "potential_conflict", conf_chunk, conf_p["potential_conflict"]
        elif sup_p["supported"] >= support_threshold:
            rel, chunk, p = "supported", sup_chunk, sup_p["supported"]
        else:
            rel, chunk, p = "ambiguous_or_insufficient", None, max(
                r[1]["ambiguous_or_insufficient"] for r in rows)
        out.append(VerifiedClaim(
            claim_id=cid, claim_text=claim["claim_text"], evidence_relationship=rel,
            retrieval_status="retrieved" if chunk else "not_retrieved",
            evidence_references=[EvidenceReference(start_seconds=chunk["start"],
                                                   end_seconds=chunk["end"])] if chunk else [],
            evidence_observations="", confidence=round(float(p), 4),
        ))
    return out
