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
from .schemas import PipelineConfig, ScenarioPrediction
from .stages.extract import extract_claims
from .stages.retrieve import retrieve_segments
from .stages.verify import verify_claim

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "benchmark"
ANNOTATIONS_DIR = BENCHMARK_DIR / "annotations"
PREDICTIONS_DIR = BENCHMARK_DIR / "predictions"

SCENARIO_TO_CASE = {
    "sc-001": "ocda-001-valdez",
    "sc-002": "ocda-002-montes",
    "sc-003": "ocda-003-emch",
    "sc-004": "ocda-004-vargas",
    "sc-005": "ocda-005-brown",
    "sc-006": "ocda-006-sanchez",
    "sc-007": "ocda-007-to",
    "sc-009": "ocda-009-steinmetz",
    "sc-011": "ocda-011-reinhold",
    "sc-013": "ocda-013-wong",
    "sc-014": "ocda-014-tran",
    "sc-015": "ocda-015-baxter",
    "sc-016": "ocda-016-salac",
    "sc-017": "ocda-017-aguirre",
    "sc-018": "ocda-018-mejia",
}


def run_claim_first(scenario_id: str, config: PipelineConfig) -> ScenarioPrediction:
    """Run the full claim-first pipeline: extract → retrieve → verify."""
    case_id = SCENARIO_TO_CASE[scenario_id]
    report_path = config.reports_dir / f"{scenario_id}_report.txt"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None

    adapter = make_adapter(config)
    start = time.time()

    print(f"  [{scenario_id}] Extracting claims from report...")
    claims = extract_claims(report_path, adapter)
    print(f"  [{scenario_id}] Extracted {len(claims)} claims")

    verified = []
    for claim in claims:
        print(f"  [{scenario_id}] {claim.claim_id}: retrieving evidence...")
        segment = retrieve_segments(claim, transcript_path, adapter)

        print(f"  [{scenario_id}] {claim.claim_id}: verifying ({segment.retrieval_status})...")
        result = verify_claim(claim, segment, adapter)
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


def get_scenarios(args) -> list[str]:
    if args.scenario:
        return [args.scenario]
    if args.all:
        return sorted(SCENARIO_TO_CASE.keys())
    return []


def main():
    parser = argparse.ArgumentParser(description="Run evidence review pipeline")
    parser.add_argument("--scenario", help="Scenario ID (e.g. sc-001)")
    parser.add_argument("--all", action="store_true", help="Run all scenarios")
    parser.add_argument("--adapter", default="claude", choices=["claude", "nemotron"])
    parser.add_argument("--model", default="claude-sonnet-5-5", help="Model ID")
    parser.add_argument("--pipeline", default="claim-first",
                        choices=["claim-first", "single-pass", "transcript-only"])
    parser.add_argument("--out", type=Path, default=PREDICTIONS_DIR)
    args = parser.parse_args()

    scenarios = get_scenarios(args)
    if not scenarios:
        parser.error("Specify --scenario or --all")

    config = default_config()
    config.model_adapter = args.adapter
    config.model_id = args.model

    args.out.mkdir(parents=True, exist_ok=True)

    for sid in scenarios:
        print(f"\n{'='*50}")
        print(f"  Running {args.pipeline} on {sid}")
        print(f"{'='*50}")

        if args.pipeline == "claim-first":
            prediction = run_claim_first(sid, config)
        elif args.pipeline == "single-pass":
            prediction = run_single_pass(sid, config)
        else:
            print(f"  Pipeline '{args.pipeline}' not yet implemented")
            continue

        out_path = args.out / f"{sid}_{args.pipeline}_{args.adapter}.json"
        with open(out_path, "w") as f:
            json.dump(prediction.to_dict(), f, indent=2)
        print(f"\n  Saved to {out_path}")
        print(f"  Time: {prediction.processing_time_seconds}s, "
              f"Tokens: {prediction.total_tokens}, "
              f"API calls: {prediction.total_api_calls}")


if __name__ == "__main__":
    main()
