"""Validate downloaded evidence files against manifest hashes.

Usage:
    python -I scripts/validate.py
"""

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


def validate_evidence(manifest: dict) -> list[str]:
    errors = []
    for source in manifest["sources"]:
        dest = EVIDENCE_DIR / source["file_name"]
        if not dest.exists():
            errors.append(f"MISSING: {source['evidence_id']} ({source['file_name']})")
            continue
        actual = sha256_file(dest)
        if actual != source["sha256"]:
            errors.append(
                f"HASH MISMATCH: {source['evidence_id']} "
                f"(expected {source['sha256'][:16]}..., got {actual[:16]}...)"
            )
        else:
            print(f"  OK: {source['evidence_id']}")
    return errors


def validate_annotations(manifest: dict) -> list[str]:
    errors = []
    evidence_ids = {s["evidence_id"] for s in manifest["sources"]}

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
    manifest = load_manifest()

    print("Validating evidence files...")
    evidence_errors = validate_evidence(manifest)

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


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


if __name__ == "__main__":
    main()
