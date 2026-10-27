"""Download benchmark evidence files from public sources.

Usage:
    python3 -I scripts/download.py                    # download all
    python3 -I scripts/download.py --scenario ocda-001 # download one case
    python3 -I scripts/download.py --list              # list sources without downloading
    python3 -I scripts/download.py --cookies cookies.txt  # pass cookies for age-restricted YouTube

For age-restricted YouTube videos (officer-involved shooting footage), use Firefox
cookies. Chrome cookie extraction is unreliable. Example:
    python3 -I scripts/download.py --cookies-from-browser firefox
"""

import argparse
import hashlib
import json
import shutil
import subprocess
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


def is_youtube_url(url: str) -> bool:
    return "youtube.com/watch" in url or "youtu.be/" in url


def download_http(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"    HTTP download failed: {e}")
        dest.unlink(missing_ok=True)
        return False


def download_ytdlp(youtube_id: str, dest: Path, cookies: str | None = None,
                    cookies_from_browser: str | None = None) -> bool:
    if not shutil.which("yt-dlp"):
        print("    yt-dlp not installed (pip install yt-dlp)")
        return False

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--remote-components", "ejs:github",
        "-o", str(dest),
        "--no-playlist",
    ]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    elif cookies:
        cmd.extend(["--cookies", cookies])

    cmd.append(f"https://www.youtube.com/watch?v={youtube_id}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            stderr = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown error"
            print(f"    yt-dlp failed: {stderr}")
            dest.unlink(missing_ok=True)
            return False
        return dest.exists()
    except FileNotFoundError:
        print("    yt-dlp not found")
        return False
    except subprocess.TimeoutExpired:
        print("    yt-dlp timed out")
        dest.unlink(missing_ok=True)
        return False


def download_source(source: dict, force: bool = False, cookies: str | None = None,
                     cookies_from_browser: str | None = None) -> bool:
    evidence_id = source["evidence_id"]
    file_name = source["file_name"]
    dest = EVIDENCE_DIR / file_name
    expected_hash = source.get("sha256")

    if dest.exists() and not force:
        if expected_hash:
            existing_hash = sha256_file(dest)
            if existing_hash == expected_hash:
                print(f"  {evidence_id}: already downloaded and verified")
                return True
            print(f"  {evidence_id}: exists but hash mismatch, re-downloading")
        else:
            print(f"  {evidence_id}: already downloaded (no hash to verify)")
            return True

    youtube_id = source.get("youtube_id")

    for url in source["urls"]:
        if is_youtube_url(url):
            if not youtube_id:
                continue
            print(f"  {evidence_id}: downloading via yt-dlp...")
            if download_ytdlp(youtube_id, dest, cookies, cookies_from_browser):
                return _verify(evidence_id, dest, expected_hash)
        else:
            print(f"  {evidence_id}: downloading from {url}")
            if download_http(url, dest):
                return _verify(evidence_id, dest, expected_hash)

    print(f"  {evidence_id}: FAILED - no working source")
    return False


def _verify(evidence_id: str, dest: Path, expected_hash: str | None) -> bool:
    size = dest.stat().st_size
    if expected_hash:
        actual_hash = sha256_file(dest)
        if actual_hash == expected_hash:
            print(f"  {evidence_id}: verified ({size:,} bytes)")
            return True
        print(f"  {evidence_id}: hash mismatch (expected {expected_hash[:16]}..., got {actual_hash[:16]}...)")
        dest.unlink(missing_ok=True)
        return False
    print(f"  {evidence_id}: downloaded ({size:,} bytes, no hash to verify)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Download benchmark evidence files")
    parser.add_argument("--scenario", help="Download only this scenario (e.g. ocda-001)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument("--list", action="store_true", help="List sources without downloading")
    parser.add_argument("--cookies", help="Path to cookies.txt for age-restricted YouTube videos")
    parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from (e.g. firefox)")
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
            expected_hash = s.get("sha256")
            if dest.exists():
                if expected_hash:
                    if sha256_file(dest) == expected_hash:
                        status = " [downloaded, verified]"
                    else:
                        status = " [downloaded, HASH MISMATCH]"
                else:
                    status = " [downloaded, no hash]"
            size = s.get("file_size_bytes")
            size_str = f" ({size:,} bytes)" if size else ""
            yt = f" [yt-dlp]" if s.get("youtube_id") and not any(not is_youtube_url(u) for u in s["urls"]) else ""
            print(f"  {s['evidence_id']}: {s['file_name']}{size_str}{status}{yt}")
            print(f"    origin: {s.get('origin', 'unknown')}")
            print(f"    url: {s['urls'][0]}")
        return

    EVIDENCE_DIR.mkdir(exist_ok=True)

    ok = 0
    fail = 0
    for source in sources:
        if download_source(source, force=args.force, cookies=args.cookies,
                           cookies_from_browser=args.cookies_from_browser):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} downloaded, {fail} failed, {len(sources)} total")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
