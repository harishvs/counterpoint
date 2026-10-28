"""Map transcript timestamps to annotation claims.

Reads transcripts from raw/transcripts/ and updates annotations with
start_seconds/end_seconds in evidence_references where a match is found.

Usage:
    python3 -I scripts/map_timestamps.py           # dry run — show matches
    python3 -I scripts/map_timestamps.py --apply    # write updated annotations
"""

import argparse
import json
import re
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPT_DIR = BENCHMARK_DIR / "raw" / "transcripts"
ANNOTATIONS_DIR = BENCHMARK_DIR / "annotations"

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


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def build_sliding_windows(segments: list[dict], window_size: int = 3) -> list[dict]:
    """Build overlapping text windows for broader matching."""
    windows = []
    for i in range(len(segments)):
        end = min(i + window_size, len(segments))
        combined_text = " ".join(normalize(s["text"]) for s in segments[i:end])
        windows.append({
            "text": combined_text,
            "start": segments[i]["start"],
            "end": segments[end - 1]["end"],
            "idx": i,
        })
    return windows


def search_transcript(segments: list[dict], keywords: list[str],
                      context_window: int = 3) -> dict | None:
    """Search transcript for keywords using sliding windows."""
    if not keywords:
        return None

    windows = build_sliding_windows(segments, window_size=3)
    best_score = 0
    best_window = None

    for win in windows:
        score = 0
        for kw in keywords:
            if kw in win["text"]:
                score += 1
                if len(kw) > 5:
                    score += 0.5

        if score > best_score:
            best_score = score
            start_idx = max(0, win["idx"] - context_window)
            end_idx = min(len(segments) - 1, win["idx"] + context_window + 2)
            best_window = {
                "start_seconds": round(segments[start_idx]["start"], 1),
                "end_seconds": round(segments[end_idx]["end"], 1),
                "match_text": win["text"][:100],
                "score": score,
            }

    return best_window


def extract_keywords(claim: dict) -> list[str]:
    """Extract search keywords from all available claim fields."""
    keywords = set()

    for ref in claim.get("evidence_references", []):
        excerpt = ref.get("transcript_excerpt", "")
        if excerpt:
            words = normalize(excerpt).split()
            keywords.update(w for w in words if len(w) > 2)

        desc = ref.get("visual_description", "")
        if desc:
            desc_lower = desc.lower()
            for phrase in EVENT_KEYWORDS:
                if phrase in desc_lower:
                    keywords.update(phrase.split())
            words = normalize(desc).split()
            keywords.update(w for w in words if len(w) > 4)

    explanation = claim.get("explanation", "")
    if explanation:
        exp_lower = explanation.lower()
        for phrase in EVENT_KEYWORDS:
            if phrase in exp_lower:
                keywords.update(phrase.split())

    claim_text = claim.get("claim_text", "")
    for quoted in re.findall(r'"([^"]*)"', claim_text):
        words = normalize(quoted).split()
        keywords.update(w for w in words if len(w) > 2)

    claim_lower = claim_text.lower()
    for phrase in EVENT_KEYWORDS:
        if phrase in claim_lower:
            keywords.update(phrase.split())

    claim_words = normalize(claim_text).split()
    keywords.update(w for w in claim_words if len(w) > 5)

    keywords.discard("")
    stopwords = {"the", "that", "this", "with", "from", "was", "were", "been",
                 "have", "had", "has", "being", "which", "their", "there",
                 "about", "would", "could", "should", "into", "also",
                 "officer", "officers", "subject", "vehicle", "report",
                 "stated", "observed", "approximately"}
    return list(keywords - stopwords)


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write updated annotations")
    parser.add_argument("--threshold", type=float, default=1.0,
                        help="Minimum match score (default: 1.0)")
    args = parser.parse_args()

    total_claims = 0
    matched = 0
    already_had = 0
    no_transcript = 0
    skipped_low = 0

    for ann_file in sorted(ANNOTATIONS_DIR.glob("*.json")):
        with open(ann_file) as f:
            ann = json.load(f)

        scenario_id = ann["scenario_id"]
        case_id = SCENARIO_TO_CASE.get(scenario_id)
        if not case_id:
            continue

        transcript_path = TRANSCRIPT_DIR / f"{case_id}.json"
        if not transcript_path.exists():
            claim_count = len(ann.get("claims", []))
            no_transcript += claim_count
            print(f"\n  {scenario_id}: no transcript (skipping {claim_count} claims)")
            continue

        with open(transcript_path) as f:
            segments = json.load(f)

        print(f"\n  {scenario_id} ({case_id}): {len(segments)} transcript segments")
        modified = False

        for claim in ann.get("claims", []):
            total_claims += 1

            has_timestamps = any(
                ref.get("start_seconds") is not None
                for ref in claim.get("evidence_references", [])
            )
            if has_timestamps:
                already_had += 1
                continue

            keywords = extract_keywords(claim)
            if not keywords:
                continue

            result = search_transcript(segments, keywords)
            if result and result["score"] >= args.threshold:
                matched += 1
                modified = True

                if claim.get("evidence_references"):
                    claim["evidence_references"][0]["start_seconds"] = result["start_seconds"]
                    claim["evidence_references"][0]["end_seconds"] = result["end_seconds"]
                else:
                    claim["evidence_references"] = [{
                        "modality": "audio",
                        "start_seconds": result["start_seconds"],
                        "end_seconds": result["end_seconds"],
                    }]

                print(f"    {claim['claim_id']}: {fmt_time(result['start_seconds'])}-{fmt_time(result['end_seconds'])} "
                      f"(score={result['score']}, kw={len(keywords)}, "
                      f"match='{result['match_text'][:50]}')")
            else:
                skipped_low += 1

        if modified and args.apply:
            with open(ann_file, "w") as f:
                json.dump(ann, f, indent=2)
                f.write("\n")
            print(f"    -> updated {ann_file.name}")

    print(f"\n--- Summary ---")
    print(f"  Total claims: {total_claims}")
    print(f"  Matched: {matched}")
    print(f"  Already had timestamps: {already_had}")
    print(f"  Below threshold: {skipped_low}")
    print(f"  No transcript available: {no_transcript}")
    if not args.apply and matched > 0:
        print(f"\n  Run with --apply to write changes")


if __name__ == "__main__":
    main()
