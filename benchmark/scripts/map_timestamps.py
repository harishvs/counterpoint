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


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def search_transcript(segments: list[dict], keywords: list[str], window: int = 5) -> dict | None:
    """Search transcript for keywords, return best matching segment with context window."""
    best_score = 0
    best_segment = None

    for i, seg in enumerate(segments):
        seg_text = normalize(seg["text"])
        score = sum(1 for kw in keywords if kw in seg_text)

        if score > best_score:
            best_score = score
            start_idx = max(0, i - window)
            end_idx = min(len(segments) - 1, i + window)
            best_segment = {
                "start_seconds": segments[start_idx]["start"],
                "end_seconds": segments[end_idx]["end"],
                "match_text": seg["text"],
                "score": score,
            }

    return best_segment if best_score > 0 else None


def extract_keywords(claim: dict) -> list[str]:
    """Extract search keywords from a claim's text and evidence references."""
    keywords = []

    for ref in claim.get("evidence_references", []):
        excerpt = ref.get("transcript_excerpt", "")
        if excerpt:
            words = normalize(excerpt).split()
            keywords.extend([w for w in words if len(w) > 3])

        desc = ref.get("visual_description", "")
        if desc:
            action_words = []
            for phrase in ["driver", "passenger", "steering wheel", "reverse",
                           "handcuff", "fired", "shots", "gun", "weapon",
                           "taser", "knife", "stop", "hands up", "get down",
                           "screaming", "running", "vehicle"]:
                if phrase in desc.lower():
                    action_words.extend(phrase.split())
            keywords.extend(action_words)

    claim_text = normalize(claim.get("claim_text", ""))
    for quoted in re.findall(r'"([^"]+)"', claim.get("claim_text", "")):
        keywords.extend([w for w in normalize(quoted).split() if len(w) > 3])

    return list(set(keywords))


def fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write updated annotations")
    args = parser.parse_args()

    total_claims = 0
    matched = 0
    already_had = 0
    no_transcript = 0

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
            if result and result["score"] >= 2:
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
                      f"(score={result['score']}, match='{result['match_text'][:60]}')")

        if modified and args.apply:
            with open(ann_file, "w") as f:
                json.dump(ann, f, indent=2)
                f.write("\n")
            print(f"    -> updated {ann_file.name}")

    print(f"\n--- Summary ---")
    print(f"  Total claims: {total_claims}")
    print(f"  Matched: {matched}")
    print(f"  Already had timestamps: {already_had}")
    print(f"  No transcript available: {no_transcript}")
    if not args.apply and matched > 0:
        print(f"\n  Run with --apply to write changes")


if __name__ == "__main__":
    main()
