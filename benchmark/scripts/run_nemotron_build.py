"""Run Nemotron Build API on all scenarios with rate-limit-friendly pacing.

Usage: python3 -I benchmark/scripts/run_nemotron_build.py
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline.config import default_config, make_adapter
from pipeline.schemas import PipelineConfig, ScenarioPrediction, RetrievedSegment
from pipeline.stages.extract import extract_claims
from pipeline.stages.retrieve import retrieve_segments
from pipeline.stages.verify import verify_claim

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = BENCHMARK_DIR / "predictions"

SCENARIOS = {
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

CALL_DELAY = 3
SCENARIO_DELAY = 10


def run_scenario(scenario_id: str, case_id: str, config: PipelineConfig) -> dict | None:
    out_path = PREDICTIONS_DIR / f"{scenario_id}_claim-first_nemotron-build.json"
    if out_path.exists():
        print(f"  [{scenario_id}] SKIP — already done")
        return None

    report_path = config.reports_dir / f"{scenario_id}_report.txt"
    transcript_path = config.transcript_dir / f"{case_id}.json" if config.transcript_dir else None

    config_copy = PipelineConfig(
        model_adapter="nemotron-build",
        model_id="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        evidence_dir=config.evidence_dir,
        reports_dir=config.reports_dir,
        transcript_dir=config.transcript_dir,
    )
    adapter = make_adapter(config_copy)
    start = time.time()

    print(f"  [{scenario_id}] Extracting claims...")
    try:
        claims = extract_claims(report_path, adapter)
    except Exception as e:
        print(f"  [{scenario_id}] Extract FAILED: {e}")
        return None
    print(f"  [{scenario_id}] Extracted {len(claims)} claims")
    time.sleep(CALL_DELAY)

    verified = []
    for claim in claims:
        if transcript_path and transcript_path.exists():
            try:
                segment = retrieve_segments(claim, transcript_path, adapter)
            except Exception as e:
                print(f"  [{scenario_id}] {claim.claim_id} retrieve failed: {e}")
                segment = RetrievedSegment(claim_id=claim.claim_id, retrieval_status="failed")
            time.sleep(CALL_DELAY)
        else:
            segment = RetrievedSegment(claim_id=claim.claim_id, retrieval_status="not_retrieved")

        try:
            result = verify_claim(claim, segment, adapter)
        except Exception as e:
            print(f"  [{scenario_id}] {claim.claim_id} verify failed: {e}")
            from pipeline.schemas import VerifiedClaim
            result = VerifiedClaim(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                evidence_relationship="not_assessed",
                retrieval_status=segment.retrieval_status,
                evidence_observations=f"Error: {str(e)[:100]}",
            )
        time.sleep(CALL_DELAY)

        verified.append(result)
        print(f"  [{scenario_id}] {claim.claim_id}: {result.evidence_relationship}")

    elapsed = time.time() - start

    prediction = ScenarioPrediction(
        scenario_id=scenario_id,
        model=adapter.model_id,
        pipeline="claim-first",
        claims=verified,
        processing_time_seconds=round(elapsed, 2),
        total_tokens=adapter.tokens_used,
        total_api_calls=adapter.api_calls,
    )

    PREDICTIONS_DIR.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(prediction.to_dict(), f, indent=2)

    print(f"  [{scenario_id}] Done: {elapsed:.0f}s, {adapter.tokens_used} tokens, {adapter.api_calls} calls")
    return prediction.to_dict()


def main():
    config = default_config()

    print(f"Running Nemotron Build API on {len(SCENARIOS)} scenarios")
    print(f"Call delay: {CALL_DELAY}s, scenario delay: {SCENARIO_DELAY}s\n")

    done = 0
    failed = 0

    for sid, case_id in SCENARIOS.items():
        print(f"\n{'='*50}")
        print(f"  {sid} ({case_id})")
        print(f"{'='*50}")

        result = run_scenario(sid, case_id, config)
        if result is not None:
            done += 1
        elif (PREDICTIONS_DIR / f"{sid}_claim-first_nemotron-build.json").exists():
            done += 1
        else:
            failed += 1

        time.sleep(SCENARIO_DELAY)

    print(f"\n{'='*50}")
    print(f"  Complete: {done} done, {failed} failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
