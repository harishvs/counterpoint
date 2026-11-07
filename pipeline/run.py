"""Run the claim-first evidence review pipeline on benchmark scenarios.

Usage:
    python3 -m pipeline.run --scenario sc-001                    # one scenario
    python3 -m pipeline.run --all                                # all scenarios
    python3 -m pipeline.run --scenario sc-001 --adapter claude   # specify adapter
    python3 -m pipeline.run --scenario sc-001 --pipeline single-pass  # baseline
"""

import argparse
import json
import time
from pathlib import Path

from .config import default_config, make_adapter
from .schemas import PipelineConfig, ScenarioPrediction, RetrievedSegment
from .stages.clip import extract_clip
from .stages.extract import extract_claims
from .stages.retrieve import retrieve_segments
from .stages.scan import scan_video
from .stages.verify import verify_claim

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "benchmark"
ANNOTATIONS_DIR = BENCHMARK_DIR / "annotations"
PREDICTIONS_DIR = BENCHMARK_DIR / "predictions"

def _build_scenario_map() -> dict[str, str]:
    """Build scenario-to-case mapping from annotation files."""
    mapping = {}
    for f in sorted(ANNOTATIONS_DIR.glob("*.json")):
        with open(f) as fh:
            ann = json.load(fh)
        case_id = ann["evidence_id"].replace("-video", "").replace("-pdf", "")
        mapping[ann["scenario_id"]] = case_id
    return mapping


SCENARIO_TO_CASE = _build_scenario_map() if ANNOTATIONS_DIR.exists() else {}


def run_claim_first(scenario_id: str, config: PipelineConfig) -> ScenarioPrediction:
    """Run the full claim-first pipeline: extract → retrieve → verify.

    When video evidence is available, cuts a clip per claim using timestamps
    from the retrieve stage (stays under Nemotron's 2-min video limit).
    """
    case_id = SCENARIO_TO_CASE[scenario_id]
    report_path = config.reports_dir / f"{scenario_id}_report.txt"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None
    video_path = config.evidence_dir / f"{case_id}-video.mp4"
    has_video = video_path.exists()
    clip_dir = config.evidence_dir / "clips"

    adapter = make_adapter(config)
    start = time.time()

    if has_video:
        print(f"  [{scenario_id}] Video available: {video_path.name}")
    else:
        print(f"  [{scenario_id}] No local video — transcript only")

    print(f"  [{scenario_id}] Extracting claims from report...")
    claims = extract_claims(report_path, adapter)
    print(f"  [{scenario_id}] Extracted {len(claims)} claims")

    verified = []
    for claim in claims:
        if transcript_path and transcript_path.exists():
            print(f"  [{scenario_id}] {claim.claim_id}: retrieving evidence...")
            segment = retrieve_segments(claim, transcript_path, adapter)
        else:
            segment = RetrievedSegment(claim_id=claim.claim_id, retrieval_status="not_retrieved")

        clip_path = None
        if has_video and segment.evidence_references:
            ref = segment.evidence_references[0]
            if ref.start_seconds is not None and ref.end_seconds is not None:
                padding = 5.0
                clip_start = max(0, ref.start_seconds - padding)
                clip_end = ref.end_seconds + padding
                clip_path = extract_clip(video_path, clip_start, clip_end, clip_dir)
                if clip_path:
                    print(f"  [{scenario_id}] {claim.claim_id}: clip {clip_start:.0f}s-{clip_end:.0f}s")

        print(f"  [{scenario_id}] {claim.claim_id}: verifying ({segment.retrieval_status})...")
        result = verify_claim(claim, segment, adapter, video_path=clip_path)
        verified.append(result)
        print(f"  [{scenario_id}] {claim.claim_id}: {result.evidence_relationship}")

    elapsed = time.time() - start

    return ScenarioPrediction(
        scenario_id=scenario_id,
        model=adapter.model_id,
        pipeline="claim-first",
        claims=verified,
        processing_time_seconds=round(elapsed, 2),
        total_tokens=adapter.tokens_used,
        total_api_calls=adapter.api_calls,
    )


def run_single_pass(scenario_id: str, config: PipelineConfig) -> ScenarioPrediction:
    """Baseline 1: Give the model the report + full transcript in one shot."""
    case_id = SCENARIO_TO_CASE[scenario_id]
    report_path = config.reports_dir / f"{scenario_id}_report.txt"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None

    adapter = make_adapter(config)
    start = time.time()

    report_text = report_path.read_text()
    transcript_text = ""
    if transcript_path and transcript_path.exists():
        with open(transcript_path) as f:
            segments = json.load(f)
        for seg in segments:
            m, s = divmod(int(seg["start"]), 60)
            transcript_text += f"[{m}:{s:02d}] {seg['text']}\n"

    prompt = (
        "You are reviewing a police incident report against bodycam evidence.\n\n"
        f"INCIDENT REPORT:\n{report_text}\n\n"
        f"BODYCAM TRANSCRIPT:\n{transcript_text}\n\n"
        "For each factual claim in the report, determine whether the bodycam evidence "
        "supports it, conflicts with it, or is ambiguous/insufficient.\n\n"
        "Return a JSON object with a 'claims' array. Each claim should have:\n"
        "- claim_id (cl-001, cl-002, etc.)\n"
        "- claim_text (the claim from the report)\n"
        "- evidence_relationship: supported | potential_conflict | ambiguous_or_insufficient | not_assessed\n"
        "- evidence_observations: what you observed in the evidence\n"
    )

    schema = {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string"},
                        "claim_text": {"type": "string"},
                        "evidence_relationship": {"type": "string"},
                        "evidence_observations": {"type": "string"},
                    },
                    "required": ["claim_id", "evidence_relationship"],
                },
            },
        },
    }

    print(f"  [{scenario_id}] Single-pass review...")
    result = adapter.complete_structured(prompt, schema)
    elapsed = time.time() - start

    from .schemas import VerifiedClaim
    verified = []
    for raw in result.get("claims", []):
        verified.append(VerifiedClaim(
            claim_id=raw["claim_id"],
            claim_text=raw.get("claim_text", ""),
            evidence_relationship=raw["evidence_relationship"],
            evidence_observations=raw.get("evidence_observations", ""),
        ))

    return ScenarioPrediction(
        scenario_id=scenario_id,
        model=adapter.model_id,
        pipeline="single-pass",
        claims=verified,
        processing_time_seconds=round(elapsed, 2),
        total_tokens=adapter.tokens_used,
        total_api_calls=adapter.api_calls,
    )


def run_video_scan(scenario_id: str, config: PipelineConfig) -> ScenarioPrediction:
    """Scan video in 2-min chunks, evaluate all claims against each chunk."""
    case_id = SCENARIO_TO_CASE[scenario_id]
    report_path = config.reports_dir / f"{scenario_id}_report.txt"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None
    video_path = config.evidence_dir / f"{case_id}-video.mp4"
    chunk_dir = config.evidence_dir / "chunks"

    if not video_path.exists():
        print(f"  [{scenario_id}] No video found at {video_path}")
        return ScenarioPrediction(scenario_id=scenario_id, model="none", pipeline="scan")

    adapter = make_adapter(config)
    start = time.time()

    print(f"  [{scenario_id}] Video: {video_path.name}")
    print(f"  [{scenario_id}] Extracting claims from report...")
    claims = extract_claims(report_path, adapter)
    print(f"  [{scenario_id}] Extracted {len(claims)} claims")
    print(f"  [{scenario_id}] Scanning video in chunks...")

    verified = scan_video(claims, video_path, transcript_path, adapter, chunk_dir)

    elapsed = time.time() - start
    conflicts = sum(1 for v in verified if v.evidence_relationship == "potential_conflict")
    supported = sum(1 for v in verified if v.evidence_relationship == "supported")
    print(f"  [{scenario_id}] Done: {conflicts} conflicts, {supported} supported, {len(verified)} total")

    return ScenarioPrediction(
        scenario_id=scenario_id,
        model=adapter.model_id,
        pipeline="scan",
        claims=verified,
        processing_time_seconds=round(elapsed, 2),
        total_tokens=adapter.tokens_used,
        total_api_calls=adapter.api_calls,
    )


def load_claims(scenario_id: str, source: str, config: PipelineConfig):
    """The claims to verify: "extract" (the LLM adapter reads the report), "gt" (the
    annotated claims, an upper bound for verification), or a predictions directory whose
    `<scenario>_*.json` claims are reused (to compare verifiers on the same claims)."""
    from .schemas import ExtractedClaim
    if source == "extract":
        return extract_claims(config.reports_dir / f"{scenario_id}_report.txt",
                              make_adapter(config))
    if source == "gt":
        with open(ANNOTATIONS_DIR / f"{scenario_id}_annotations.json") as fh:
            rows = json.load(fh)["claims"]
    else:
        files = sorted(Path(source).glob(f"{scenario_id}_*.json"))
        if not files:
            raise FileNotFoundError(f"no {scenario_id}_*.json in {source}")
        with open(files[0]) as fh:
            rows = json.load(fh)["claims"]
    return [ExtractedClaim(claim_id=r["claim_id"], claim_text=r["claim_text"],
                           report_location=r.get("report_location", "")) for r in rows]


def run_swiftpick_scan(scenario_id: str, config: PipelineConfig, args) -> ScenarioPrediction:
    """Short chunks, every claim a choice question, answered by a swiftpick server."""
    from .stages.decide import SwiftpickClient, aggregate, scan
    case_id = SCENARIO_TO_CASE[scenario_id]
    video_path = config.evidence_dir / f"{case_id}-video.mp4"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None
    if not video_path.exists():
        print(f"  [{scenario_id}] No video found at {video_path}")
        return ScenarioPrediction(scenario_id=scenario_id, model="none", pipeline="swiftpick-scan")
    client = SwiftpickClient(args.endpoint.removesuffix("/v1"))
    start = time.time()
    claims = load_claims(scenario_id, args.claims_from, config)
    print(f"  [{scenario_id}] {len(claims)} claims from {args.claims_from}")
    raw = scan(claims, video_path, transcript_path, client, config.evidence_dir / "chunks-swiftpick",
               length=args.chunk_seconds, stride=args.stride, with_audio=not args.no_audio)
    raw["scenario_id"], raw["claims_from"] = scenario_id, args.claims_from
    raw_dir = args.out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with open(raw_dir / f"{scenario_id}_swiftpick-scan_raw.json", "w") as fh:
        json.dump(raw, fh)
    return ScenarioPrediction(
        scenario_id=scenario_id, model=client.health().get("model", "swiftpick"),
        pipeline="swiftpick-scan", claims=aggregate(raw, args.conflict_threshold),
        processing_time_seconds=round(time.time() - start, 2),
        total_tokens=client.tokens, total_api_calls=client.calls,
    )


def get_scenarios(args) -> list[str]:
    if args.scenario:
        return [args.scenario]
    if args.all:
        ids = sorted(SCENARIO_TO_CASE.keys())
        if args.shard:  # "i/n": every n-th scenario from the i-th, to run n servers at once
            i, n = (int(x) for x in args.shard.split("/"))
            ids = ids[i::n]
        return ids
    return []


def main():
    parser = argparse.ArgumentParser(description="Run evidence review pipeline")
    parser.add_argument("--scenario", help="Scenario ID (e.g. sc-001)")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--adapter", default="claude", choices=["claude", "nemotron", "nemotron-build"])
    parser.add_argument("--model", default="claude-haiku-5-5", help="Model ID")
    parser.add_argument("--bedrock", action="store_true", default=True, help="Use AWS Bedrock")
    parser.add_argument("--no-bedrock", dest="bedrock", action="store_false")
    parser.add_argument("--endpoint", default="http://localhost:8000/v1",
                        help="Model endpoint URL (for Nemotron/vLLM)")
    parser.add_argument("--pipeline", default="claim-first",
                        choices=["claim-first", "single-pass", "scan", "swiftpick-scan"])
    parser.add_argument("--claims-from", default="extract",
                        help='swiftpick-scan: "extract", "gt", or a predictions directory')
    parser.add_argument("--chunk-seconds", type=float, default=20.0)
    parser.add_argument("--stride", type=float, default=15.0)
    parser.add_argument("--no-audio", action="store_true",
                        help="swiftpick-scan: do not send each chunk's audio")
    parser.add_argument("--conflict-threshold", type=float, default=0.5)
    parser.add_argument("--shard", help='with --all: "i/n", run every n-th scenario from the i-th')
    parser.add_argument("--out", type=Path, default=PREDICTIONS_DIR)
    args = parser.parse_args()

    scenarios = get_scenarios(args)
    if not scenarios:
        parser.error("Specify --scenario or --all")

    config = default_config()
    config.model_adapter = args.adapter
    config.model_id = args.model
    config.use_bedrock = args.bedrock
    config.nemotron_endpoint = args.endpoint

    args.out.mkdir(parents=True, exist_ok=True)

    for sid in scenarios:
        print(f"\n{'='*50}")
        print(f"  Running {args.pipeline} on {sid}")
        print(f"{'='*50}")

        if args.pipeline == "claim-first":
            prediction = run_claim_first(sid, config)
        elif args.pipeline == "single-pass":
            prediction = run_single_pass(sid, config)
        elif args.pipeline == "scan":
            prediction = run_video_scan(sid, config)
        elif args.pipeline == "swiftpick-scan":
            prediction = run_swiftpick_scan(sid, config, args)
        else:
            print(f"  Pipeline '{args.pipeline}' not yet implemented")
            continue

        tag = "swiftpick" if args.pipeline == "swiftpick-scan" else args.adapter
        out_path = args.out / f"{sid}_{args.pipeline}_{tag}.json"
        with open(out_path, "w") as f:
            json.dump(prediction.to_dict(), f, indent=2)
        print(f"\n  Saved to {out_path}")
        print(f"  Time: {prediction.processing_time_seconds}s, "
              f"Tokens: {prediction.total_tokens}, "
              f"API calls: {prediction.total_api_calls}")


if __name__ == "__main__":
    main()
