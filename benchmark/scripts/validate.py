"""Validate downloaded evidence files against manifest hashes.

Usage:
    python3 -I scripts/validate.py              # validate downloaded files only
    python3 -I scripts/validate.py --strict     # fail if any manifest source is missing
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BENCHMARK_DIR / "manifest.json"
EVIDENCE_DIR = BENCHMARK_DIR / "evidence"
ANNOTATIONS_DIR = BENCHMARK_DIR / "annotations"
REPORTS_DIR = BENCHMARK_DIR / "reports"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def validate_evidence(manifest: dict, strict: bool = False) -> list[str]:
    errors = []
    missing = 0
    for source in manifest["sources"]:
        dest = EVIDENCE_DIR / source["file_name"]
        if not dest.exists():
            missing += 1
            if strict:
                errors.append(f"MISSING: {source['evidence_id']} ({source['file_name']})")
            continue
        expected = source.get("sha256")
        if expected:
            actual = sha256_file(dest)
            if actual != expected:
                errors.append(
                    f"HASH MISMATCH: {source['evidence_id']} "
                    f"(expected {expected[:16]}..., got {actual[:16]}...)"
                )
            else:
                print(f"  OK: {source['evidence_id']}")
        else:
            print(f"  OK: {source['evidence_id']} (no hash, size={dest.stat().st_size:,})")
    if missing and not strict:
        print(f"  ({missing} source(s) not yet downloaded — run download.py first)")
    return errors


def validate_annotations(manifest: dict) -> list[str]:
    errors = []
    evidence_ids = {s["evidence_id"] for s in manifest["sources"]}

    if not ANNOTATIONS_DIR.exists():
        print("  (no annotations directory yet)")
        return errors

    for ann_file in sorted(ANNOTATIONS_DIR.glob("*.json")):
        with open(ann_file) as f:
            ann = json.load(f)

        scenario_id = ann.get("scenario_id", "unknown")

        if ann["evidence_id"] not in evidence_ids:
            errors.append(
                f"{scenario_id}: evidence_id '{ann['evidence_id']}' not in manifest"
            )

        report_path = REPORTS_DIR / ann["report_id"]
        if not report_path.exists():
            errors.append(f"{scenario_id}: report '{ann['report_id']}' not found")

        for claim in ann.get("claims", []):
            if not claim.get("explanation"):
                errors.append(
                    f"{scenario_id}/{claim['claim_id']}: missing explanation"
                )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate benchmark evidence and annotations")
    parser.add_argument("--strict", action="store_true", help="Fail if any manifest source is not downloaded")
    args = parser.parse_args()

    manifest = load_manifest()

    print("Validating evidence files...")
    evidence_errors = validate_evidence(manifest, strict=args.strict)

    print("\nValidating annotations...")
    annotation_errors = validate_annotations(manifest)

    all_errors = evidence_errors + annotation_errors
    if all_errors:
        print(f"\n{len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nAll checks passed.")


if __name__ == "__main__":
    main()
