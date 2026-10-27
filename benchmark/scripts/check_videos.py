"""Check YouTube and Internet Archive video availability for all cases.

Usage: python3 -I scripts/check_videos.py
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent

CASES = [
    {"id": "ocda-001-valdez", "yt": "YEzm8dyxOMI", "ia": "ocda-report-officer-involved-shooting-jose-david-valdez-yezm-8dyx-omi"},
    {"id": "ocda-002-montes", "yt": "B5KzBbXR2D4", "ia": None},
    {"id": "ocda-003-emch", "yt": "KdsaDvym7w8", "ia": None},
    {"id": "ocda-004-vargas", "yt": "QM3rJCuCz_0", "ia": None},
    {"id": "ocda-005-brown", "yt": "-X4H21dTIms", "ia": None},
    {"id": "ocda-006-sanchez", "yt": "8mfhxmo8cL4", "ia": None},
    {"id": "ocda-007-to", "yt": "DmRtfF2KWso", "ia": None},
    {"id": "ocda-008-tice", "yt": "c_bpcXSP6EI", "ia": None},
    {"id": "ocda-009-steinmetz", "yt": "eF51P_XNql0", "ia": None},
    {"id": "ocda-011-reinhold", "yt": "OZjT3eE3u-Q", "ia": None},
    {"id": "ocda-013-wong", "yt": "Kqf-FJti5A4", "ia": None},
    {"id": "ocda-014-tran", "yt": "PEqVtC1Yn4k", "ia": None},
    {"id": "ocda-015-baxter", "yt": "xJF5_fUBn1c", "ia": None},
    {"id": "ocda-016-salac", "yt": "-TSzqer7D7Q", "ia": None},
    {"id": "ocda-017-aguirre", "yt": "05fURkLaYcc", "ia": None},
    {"id": "ocda-018-mejia", "yt": "sDMtt564DWw", "ia": None},
]


def check_youtube(video_id: str) -> dict | None:
    """Check YouTube oEmbed for video availability. Returns metadata or None."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def search_ia_by_youtube_id(yt_id: str) -> str | None:
    """Search Internet Archive for an item containing this YouTube ID."""
    query = urllib.parse.quote(f"ocda {yt_id}")
    url = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier&rows=5&output=json"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        docs = data.get("response", {}).get("docs", [])
        for doc in docs:
            ident = doc.get("identifier", "")
            if "ocda" in ident.lower():
                return ident
        return None
    except Exception:
        return None


def get_ia_files(identifier: str) -> list[dict] | None:
    """Get file listing for an IA item."""
    url = f"https://archive.org/metadata/{identifier}/files"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        return data.get("result", [])
    except Exception:
        return None


def main():
    print("=== YouTube availability ===\n")
    yt_results = []
    for case in CASES:
        info = check_youtube(case["yt"])
        if info:
            title = info.get("title", "?")
            print(f"  OK  {case['id']}: {title}")
            yt_results.append({"id": case["id"], "yt": case["yt"], "title": title, "alive": True})
        else:
            print(f"  DEAD {case['id']}: YouTube ID {case['yt']}")
            yt_results.append({"id": case["id"], "yt": case["yt"], "title": None, "alive": False})

    alive_yt = sum(1 for r in yt_results if r["alive"])
    print(f"\n  YouTube: {alive_yt}/{len(CASES)} alive\n")

    print("=== Internet Archive search ===\n")
    ia_results = []
    for case in CASES:
        known_ia = case.get("ia")
        if known_ia:
            files = get_ia_files(known_ia)
            if files is not None:
                mp4s = [f for f in files if f.get("name", "").endswith(".mp4")]
                print(f"  OK  {case['id']}: known IA id '{known_ia}' — {len(mp4s)} mp4(s)")
                ia_results.append({"id": case["id"], "ia_id": known_ia, "files": [f["name"] for f in mp4s]})
                continue
            else:
                print(f"  FAIL {case['id']}: known IA id '{known_ia}' — metadata fetch failed")

        found = search_ia_by_youtube_id(case["yt"])
        if found:
            files = get_ia_files(found)
            mp4s = [f for f in (files or []) if f.get("name", "").endswith(".mp4")]
            print(f"  FOUND {case['id']}: IA id '{found}' — {len(mp4s)} mp4(s)")
            ia_results.append({"id": case["id"], "ia_id": found, "files": [f["name"] for f in mp4s]})
        else:
            print(f"  NONE {case['id']}: no IA mirror found for YT {case['yt']}")
            ia_results.append({"id": case["id"], "ia_id": None, "files": []})

    found_ia = sum(1 for r in ia_results if r["ia_id"])
    print(f"\n  IA mirrors: {found_ia}/{len(CASES)} found\n")

    combined = []
    for yt, ia in zip(yt_results, ia_results):
        combined.append({**yt, "ia_id": ia["ia_id"], "ia_mp4s": ia["files"]})

    out_path = BENCHMARK_DIR / "scripts" / "_video_results.json"
    with open(out_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
