"""Download benchmark evidence files from public sources.

Usage:
    python -I scripts/download.py                  # download all
    python -I scripts/download.py --scenario sc-001 # download one
    python -I scripts/download.py --list            # list sources without downloading
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = BENCHMARK_DIR / "manifest.json"
EVIDENCE_DIR = BENCHMARK_DIR / "evidence"


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_source(source: dict, force: bool = False) -> bool:
    evidence_id = source["evidence_id"]
    file_name = source["file_name"]
    dest = EVIDENCE_DIR / file_name

    if dest.exists() and not force:
        existing_hash = sha256_file(dest)
        if existing_hash == source["sha256"]:
            print(f"  {evidence_id}: already downloaded and verified")
            return True
        print(f"  {evidence_id}: exists but hash mismatch, re-downloading")

    for url in source["urls"]:
        print(f"  {evidence_id}: downloading from {url}")
        try:
            urllib.request.urlretrieve(url, dest)
            actual_hash = sha256_file(dest)
            if actual_hash == source["sha256"]:
                print(f"  {evidence_id}: verified ({dest.stat().st_size:,} bytes)")
                return True
            print(f"  {evidence_id}: hash mismatch (expected {source['sha256'][:16]}..., got {actual_hash[:16]}...)")
            dest.unlink(missing_ok=True)
        except Exception as e:
            print(f"  {evidence_id}: failed from {url}: {e}")
            dest.unlink(missing_ok=True)

    print(f"  {evidence_id}: FAILED - no working URL")
    return False


def main():
    parser = argparse.ArgumentParser(description="Download benchmark evidence files")
    parser.add_argument("--scenario", help="Download only this scenario (e.g. sc-001)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument("--list", action="store_true", help="List sources without downloading")
    args = parser.parse_args()

    manifest = load_manifest()
    sources = manifest["sources"]

    if args.scenario:
        sources = [s for s in sources if args.scenario in s["evidence_id"]]
        if not sources:
            print(f"No sources found for scenario {args.scenario}")
            sys.exit(1)

    if args.list:
        for s in sources:
            status = ""
            dest = EVIDENCE_DIR / s["file_name"]
            if dest.exists():
                if sha256_file(dest) == s["sha256"]:
                    status = " [downloaded, verified]"
                else:
                    status = " [downloaded, HASH MISMATCH]"
            size = s.get("file_size_bytes")
            size_str = f" ({size:,} bytes)" if size else ""
            print(f"  {s['evidence_id']}: {s['file_name']}{size_str}{status}")
            print(f"    origin: {s.get('origin', 'unknown')}")
            print(f"    url: {s['urls'][0]}")
        return

    EVIDENCE_DIR.mkdir(exist_ok=True)

    ok = 0
    fail = 0
    for source in sources:
        if download_source(source, force=args.force):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} downloaded, {fail} failed, {len(sources)} total")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
