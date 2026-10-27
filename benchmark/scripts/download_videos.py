"""Download all 16 bodycam videos and compute SHA-256 hashes.

Uses IA direct download where available, yt-dlp for YouTube-only cases.

Usage: python3 -I scripts/download_videos.py
"""

import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BENCHMARK_DIR / "evidence"

VIDEOS = [
    {
        "case_id": "ocda-001-valdez",
        "yt_id": "YEzm8dyxOMI",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-jose-david-valdez-yezm-8dyx-omi/OCDA%20REPORT%20OFFICER-INVOLVED%20SHOOTING%20-%20Jose%20David%20Valdez%20%5BYEzm8dyxOMI%5D.mp4",
    },
    {
        "case_id": "ocda-002-montes",
        "yt_id": "B5KzBbXR2D4",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-alejandro-sanchez-montes-b-5-kz-bb-xr-2-d-4/OCDA%20REPORT%EF%BC%9A%20OFFICER-INVOLVED%20SHOOTING%20-%20Alejandro%20Sanchez%20Montes%20%5BB5KzBbXR2D4%5D.mp4",
    },
    {
        "case_id": "ocda-003-emch",
        "yt_id": "KdsaDvym7w8",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-michael-emch-kdsa-dvym-7w-8/OCDA%20REPORT%EF%BC%9A%20OFFICER-INVOLVED%20SHOOTING%20-%20Michael%20Emch%20%5BKdsaDvym7w8%5D.mp4",
    },
    {
        "case_id": "ocda-004-vargas",
        "yt_id": "QM3rJCuCz_0",
        "ia_url": None,
    },
    {
        "case_id": "ocda-005-brown",
        "yt_id": "-X4H21dTIms",
        "ia_url": None,
    },
    {
        "case_id": "ocda-006-sanchez",
        "yt_id": "8mfhxmo8cL4",
        "ia_url": None,
    },
    {
        "case_id": "ocda-007-to",
        "yt_id": "DmRtfF2KWso",
        "ia_url": None,
    },
    {
        "case_id": "ocda-008-tice",
        "yt_id": "c_bpcXSP6EI",
        "ia_url": "https://archive.org/download/ocda-report-officer-involed-shooting-hunter-tice-c-bpc-xsp-6-ei/OCDA%20REPORT%EF%BC%9A%20OFFICER-INVOLED%20SHOOTING%20-%20Hunter%20Tice%20%5Bc_bpcXSP6EI%5D.mp4",
    },
    {
        "case_id": "ocda-009-steinmetz",
        "yt_id": "eF51P_XNql0",
        "ia_url": None,
    },
    {
        "case_id": "ocda-011-reinhold",
        "yt_id": "OZjT3eE3u-Q",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-kurt-reinhold-ozj-t-3e-e-3u-q/OCDA%20Report%20Officer-Involved%20Shooting%20-%20Kurt%20Reinhold%20%5BOZjT3eE3u-Q%5D.mp4",
    },
    {
        "case_id": "ocda-013-wong",
        "yt_id": "Kqf-FJti5A4",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-matthew-wong-kqf-fjti-5-a-4/OCDA%20REPORT%20OFFICER-INVOLVED%20SHOOTING%20-%20Matthew%20Wong%20%5BKqf-FJti5A4%5D.mp4",
    },
    {
        "case_id": "ocda-014-tran",
        "yt_id": "PEqVtC1Yn4k",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-matthew-tuan-ahn-tran-peq-vt-c-1-yn-4k/OCDA%20REPORT%20OFFICER-INVOLVED%20SHOOTING%20-%20Matthew-Tuan%20Ahn%20Tran%20%5BPEqVtC1Yn4k%5D.mp4",
    },
    {
        "case_id": "ocda-015-baxter",
        "yt_id": "xJF5_fUBn1c",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-cedric-baxter-x-jf-5-f-ubn-1c/OCDA%20REPORT%EF%BC%9A%20OFFICER-INVOLVED%20SHOOTING%20-%20Cedric%20Baxter%20%5BxJF5_fUBn1c%5D.mp4",
    },
    {
        "case_id": "ocda-016-salac",
        "yt_id": "-TSzqer7D7Q",
        "ia_url": None,
    },
    {
        "case_id": "ocda-017-aguirre",
        "yt_id": "05fURkLaYcc",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-randolph-valendino-aguirre-05f-urk-la-ycc/OCDA%20Report%20Officer-Involved%20Shooting%20-%20Randolph%20Valendino%20Aguirre%20%5B05fURkLaYcc%5D.mp4",
    },
    {
        "case_id": "ocda-018-mejia",
        "yt_id": "sDMtt564DWw",
        "ia_url": "https://archive.org/download/ocda-report-officer-involved-shooting-clemente-de-garay-mejia-s-dmtt-564-dww/OCDA%20REPORT%EF%BC%9A%20OFFICER-INVOLVED%20SHOOTING%20-%20Clemente%20De%20Garay%20Mejia%20%5BsDMtt564DWw%5D.mp4",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_ia(url: str, dest: Path) -> bool:
    print(f"    Downloading from Internet Archive...")
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"    IA download failed: {e}")
        return False


def download_ytdlp(yt_id: str, dest: Path) -> bool:
    print(f"    Downloading from YouTube via yt-dlp...")
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "-o", str(dest),
                "--no-playlist",
                f"https://www.youtube.com/watch?v={yt_id}",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"    yt-dlp error: {result.stderr[-200:]}")
            return False
        return dest.exists()
    except FileNotFoundError:
        print("    yt-dlp not installed")
        return False
    except Exception as e:
        print(f"    yt-dlp failed: {e}")
        return False


def main():
    EVIDENCE_DIR.mkdir(exist_ok=True)

    print(f"Downloading {len(VIDEOS)} videos...\n")
    results = []

    for v in VIDEOS:
        fname = f"{v['case_id']}-video.mp4"
        dest = EVIDENCE_DIR / fname
        print(f"  [{v['case_id']}]")

        if dest.exists():
            sha = sha256_file(dest)
            size = dest.stat().st_size
            print(f"    Already exists: {size:,} bytes  sha256={sha[:16]}...")
            results.append({
                "case_id": v["case_id"],
                "yt_id": v["yt_id"],
                "ia_url": v["ia_url"],
                "file_name": fname,
                "sha256": sha,
                "size": size,
                "source": "cached",
            })
            continue

        ok = False
        source = None

        if v["ia_url"]:
            ok = download_ia(v["ia_url"], dest)
            if ok:
                source = "ia"

        if not ok:
            ok = download_ytdlp(v["yt_id"], dest)
            if ok:
                source = "yt-dlp"

        if ok and dest.exists():
            sha = sha256_file(dest)
            size = dest.stat().st_size
            print(f"    OK ({source}): {size:,} bytes  sha256={sha[:16]}...")
            results.append({
                "case_id": v["case_id"],
                "yt_id": v["yt_id"],
                "ia_url": v["ia_url"],
                "file_name": fname,
                "sha256": sha,
                "size": size,
                "source": source,
            })
        else:
            print(f"    FAILED")
            results.append({
                "case_id": v["case_id"],
                "yt_id": v["yt_id"],
                "ia_url": v["ia_url"],
                "file_name": fname,
                "sha256": None,
                "size": None,
                "source": "failed",
            })

    out_path = BENCHMARK_DIR / "scripts" / "_video_downloads.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    ok_count = sum(1 for r in results if r["sha256"])
    print(f"\nDone: {ok_count}/{len(VIDEOS)} downloaded")
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
