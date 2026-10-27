"""Verify IA matches are correct and get mp4 filenames."""

import json
import urllib.request
import urllib.parse
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent

IA_MATCHES = [
    ("ocda-001-valdez", "YEzm8dyxOMI", "ocda-report-officer-involved-shooting-jose-david-valdez-yezm-8dyx-omi"),
    ("ocda-002-montes", "B5KzBbXR2D4", "ocda-report-officer-involved-shooting-alejandro-sanchez-montes-b-5-kz-bb-xr-2-d-4"),
    ("ocda-003-emch", "KdsaDvym7w8", "ocda-report-officer-involved-shooting-michael-emch-kdsa-dvym-7w-8"),
    ("ocda-005-brown", "-X4H21dTIms", "ocda-report-officer-involved-shooting-kurt-reinhold-ozj-t-3e-e-3u-q"),
    ("ocda-008-tice", "c_bpcXSP6EI", "ocda-report-officer-involed-shooting-hunter-tice-c-bpc-xsp-6-ei"),
    ("ocda-011-reinhold", "OZjT3eE3u-Q", "ocda-report-officer-involved-shooting-kurt-reinhold-ozj-t-3e-e-3u-q"),
    ("ocda-013-wong", "Kqf-FJti5A4", "ocda-report-officer-involved-shooting-matthew-wong-kqf-fjti-5-a-4"),
    ("ocda-014-tran", "PEqVtC1Yn4k", "ocda-report-officer-involved-shooting-matthew-tuan-ahn-tran-peq-vt-c-1-yn-4k"),
    ("ocda-015-baxter", "xJF5_fUBn1c", "ocda-report-officer-involved-shooting-cedric-baxter-x-jf-5-f-ubn-1c"),
    ("ocda-016-salac", "-TSzqer7D7Q", "ocda-report-officer-involved-shooting-jose-david-valdez-yezm-8dyx-omi"),
    ("ocda-017-aguirre", "05fURkLaYcc", "ocda-report-officer-involved-shooting-randolph-valendino-aguirre-05f-urk-la-ycc"),
    ("ocda-018-mejia", "sDMtt564DWw", "ocda-report-officer-involved-shooting-clemente-de-garay-mejia-s-dmtt-564-dww"),
]


def yt_id_in_ia_identifier(yt_id: str, ia_id: str) -> bool:
    """Check if the YouTube ID appears (lowercased, possibly hyphenated) in the IA identifier."""
    clean = yt_id.lower().replace("_", "-").replace("-", "")
    ia_clean = ia_id.replace("-", "")
    return clean in ia_clean


def get_ia_metadata(identifier: str) -> dict | None:
    url = f"https://archive.org/metadata/{identifier}/files"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"    Error fetching metadata: {e}")
        return None


def main():
    verified = []

    for case_id, yt_id, ia_id in IA_MATCHES:
        match = yt_id_in_ia_identifier(yt_id, ia_id)
        if not match:
            print(f"  REJECT {case_id}: IA '{ia_id}' does not match YT '{yt_id}' — false search result")
            continue

        data = get_ia_metadata(ia_id)
        if not data:
            print(f"  FAIL {case_id}: couldn't fetch metadata for '{ia_id}'")
            continue

        files = data.get("result", [])
        mp4s = [f for f in files if f.get("name", "").endswith(".mp4")]
        if not mp4s:
            print(f"  NO_MP4 {case_id}: IA '{ia_id}' has no mp4 files")
            continue

        for mp4 in mp4s:
            fname = mp4["name"]
            size = int(mp4.get("size", 0))
            dl_url = f"https://archive.org/download/{ia_id}/{urllib.parse.quote(fname)}"
            print(f"  OK  {case_id}: {fname} ({size:,} bytes)")
            print(f"       {dl_url}")
            verified.append({
                "case_id": case_id,
                "yt_id": yt_id,
                "ia_id": ia_id,
                "mp4_name": fname,
                "mp4_size": size,
                "dl_url": dl_url,
            })

    out_path = BENCHMARK_DIR / "scripts" / "_ia_verified.json"
    with open(out_path, "w") as f:
        json.dump(verified, f, indent=2)
    print(f"\nVerified {len(verified)} IA mirrors → {out_path}")


if __name__ == "__main__":
    main()
