"""Pull YouTube auto-generated subtitles for all videos and save as JSON transcripts.

Run on a local machine with Firefox cookies:
    python3 -I scripts/pull_transcripts.py --cookies-from-browser firefox

Output: raw/transcripts/{case_id}.json with timestamped segments.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPT_DIR = BENCHMARK_DIR / "raw" / "transcripts"

VIDEOS = [
    ("ocda-001-valdez", "YEzm8dyxOMI"),
    ("ocda-002-montes", "B5KzBbXR2D4"),
    ("ocda-003-emch", "KdsaDvym7w8"),
    ("ocda-004-vargas", "QM3rJCuCz_0"),
    ("ocda-005-brown", "-X4H21dTIms"),
    ("ocda-006-sanchez", "8mfhxmo8cL4"),
    ("ocda-007-to", "DmRtfF2KWso"),
    ("ocda-009-steinmetz", "eF51P_XNql0"),
    ("ocda-011-reinhold", "OZjT3eE3u-Q"),
    ("ocda-013-wong", "Kqf-FJti5A4"),
    ("ocda-014-tran", "PEqVtC1Yn4k"),
    ("ocda-015-baxter", "xJF5_fUBn1c"),
    ("ocda-016-salac", "-TSzqer7D7Q"),
    ("ocda-017-aguirre", "05fURkLaYcc"),
    ("ocda-018-mejia", "sDMtt564DWw"),
]


def parse_vtt(vtt_path: Path) -> list[dict]:
    """Parse a .vtt subtitle file into timestamped segments."""
    text = vtt_path.read_text(encoding="utf-8")
    segments = []
    ts_pattern = re.compile(r"(\d+):(\d+):(\d+)\.(\d+)\s+-->\s+(\d+):(\d+):(\d+)\.(\d+)")

    blocks = text.split("\n\n")
    seen_texts = set()

    for block in blocks:
        lines = block.strip().split("\n")
        for i, line in enumerate(lines):
            match = ts_pattern.search(line)
            if match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = match.groups()
                start = int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000
                end = int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000
                caption_lines = [l for l in lines[i + 1:] if l.strip() and not l.strip().isdigit()]
                caption = " ".join(caption_lines)
                caption = re.sub(r"<[^>]+>", "", caption).strip()
                if caption and caption not in seen_texts:
                    seen_texts.add(caption)
                    segments.append({
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "text": caption,
                    })

    return segments


def pull_transcript(case_id: str, yt_id: str, cookies_arg: list[str], tmp_dir: Path) -> list[dict] | None:
    """Use yt-dlp to download auto-subs, parse into segments."""
    out_template = str(tmp_dir / case_id)

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "vtt",
        "--skip-download",
        "--remote-components", "ejs:github",
        "-o", out_template,
        "--no-playlist",
    ] + cookies_arg + [f"https://www.youtube.com/watch?v={yt_id}"]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    vtt_candidates = list(tmp_dir.glob(f"{case_id}*.vtt"))
    if not vtt_candidates:
        stderr_last = result.stderr.strip().split("\n")[-1] if result.stderr else "unknown"
        print(f"  FAIL {case_id}: no subtitle file produced — {stderr_last}")
        return None

    segments = parse_vtt(vtt_candidates[0])
    for f in vtt_candidates:
        f.unlink()
    return segments


def main():
    parser = argparse.ArgumentParser(description="Pull YouTube transcripts for all benchmark videos")
    parser.add_argument("--cookies", help="Path to cookies.txt")
    parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from (e.g. firefox)")
    args = parser.parse_args()

    cookies_arg = []
    if args.cookies_from_browser:
        cookies_arg = ["--cookies-from-browser", args.cookies_from_browser]
    elif args.cookies:
        cookies_arg = ["--cookies", args.cookies]

    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = BENCHMARK_DIR / "raw" / "_tmp_subs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    fail = 0

    for case_id, yt_id in VIDEOS:
        out_path = TRANSCRIPT_DIR / f"{case_id}.json"
        if out_path.exists():
            with open(out_path) as f:
                existing = json.load(f)
            print(f"  SKIP {case_id}: already have {len(existing)} segments")
            ok += 1
            continue

        print(f"  PULL {case_id} (YT: {yt_id})...")
        segments = pull_transcript(case_id, yt_id, cookies_arg, tmp_dir)

        if segments:
            with open(out_path, "w") as f:
                json.dump(segments, f, indent=2)
            print(f"  OK   {case_id}: {len(segments)} segments, {segments[-1]['end']:.0f}s total")
            ok += 1
        else:
            fail += 1

    tmp_dir.rmdir()

    print(f"\nDone: {ok} transcripts, {fail} failed")


if __name__ == "__main__":
    main()
