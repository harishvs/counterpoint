"""Check which OCDA PDF URLs are still reachable.

Usage: python -I scripts/check_urls.py
"""

import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = BENCHMARK_DIR / "evidence"

OCDA_BASE = "https://ocdistrictattorney.gov"

CASES = [
    {
        "id": "ocda-001-valdez",
        "subject": "Jose David Valdez",
        "agency": "Costa Mesa PD",
        "pdf_path": "/wp-content/uploads/2022/11/Valdez-OIS-SA-21-000554-Final-Signed-letter.pdf",
        "youtube_id": "YEzm8dyxOMI",
        "ia_id": "ocda-report-officer-involved-shooting-jose-david-valdez-yezm-8dyx-omi",
    },
    {
        "id": "ocda-002-montes",
        "subject": "Alejandro Sanchez Montes",
        "agency": "Santa Ana PD",
        "pdf_path": "/wp-content/uploads/2023/10/Montes-Alejandro-SAPD-SA-22-003506-Final-Signed-Letter.pdf",
        "youtube_id": "B5KzBbXR2D4",
        "ia_id": None,
    },
    {
        "id": "ocda-003-emch",
        "subject": "Michael Emch Jr",
        "agency": "Seal Beach PD",
        "pdf_path": "/wp-content/uploads/2023/12/Emch-Michael-SBPD-SA-23-000134-Final-Signed-Letter-2.pdf",
        "youtube_id": "KdsaDvym7w8",
        "ia_id": None,
    },
    {
        "id": "ocda-004-vargas",
        "subject": "Hugo Vargas",
        "agency": "Costa Mesa PD",
        "pdf_path": "/wp-content/uploads/2023/08/Vargas-Hugo-CMPD-SA-22-002116-Final-Signed-Letter-1.pdf",
        "youtube_id": "QM3rJCuCz_0",
        "ia_id": None,
    },
    {
        "id": "ocda-005-brown",
        "subject": "Osman Brown",
        "agency": "Anaheim PD",
        "pdf_path": "/wp-content/uploads/2023/07/Brown-Osman-APD-SA-22-000588-Completed-and-Signed-Letter-6.7.2023.pdf",
        "youtube_id": "-X4H21dTIms",
        "ia_id": None,
    },
    {
        "id": "ocda-006-sanchez",
        "subject": "Raul Sanchez",
        "agency": "Anaheim PD",
        "pdf_path": "/wp-content/uploads/2023/07/Sanchez-APD-SA-20-030-Completed-and-Signed-Letter.pdf",
        "youtube_id": "8mfhxmo8cL4",
        "ia_id": None,
    },
    {
        "id": "ocda-007-to",
        "subject": "Khang Chi To",
        "agency": "Westminster PD",
        "pdf_path": "/wp-content/uploads/2024/03/To-Khang-WPD-SA-22-003949-Final-Signed-Letter-Revised.pdf",
        "youtube_id": "DmRtfF2KWso",
        "ia_id": None,
    },
    {
        "id": "ocda-008-tice",
        "subject": "Hunter Tice",
        "agency": "Unknown",
        "pdf_path": "/wp-content/uploads/2023/12/Tice-Hunter-OIS-News-Release.pdf",
        "youtube_id": "c_bpcXSP6EI",
        "ia_id": None,
    },
    {
        "id": "ocda-009-steinmetz",
        "subject": "Tobiah Paul Steinmetz",
        "agency": "Long Beach PD",
        "pdf_path": "/wp-content/uploads/2023/10/Steinmetz-Tobiah-Paul-LBPD-SA-21-835-Final-Signed-Letter.pdf",
        "youtube_id": "eF51P_XNql0",
        "ia_id": None,
    },
    {
        "id": "ocda-010-hernandez",
        "subject": "Hector Hernandez",
        "agency": "Fullerton PD",
        "pdf_path": "/investigation-letters/Hernandez S.A. 20-014 FINAL July 27 2021.pdf",
        "youtube_id": "TouOkdy-ytQ",
        "ia_id": None,
    },
    {
        "id": "ocda-011-reinhold",
        "subject": "Kurt Reinhold",
        "agency": "OC Sheriff",
        "pdf_path": "/wp-content/uploads/2022/02/Reinhold-Final-Signed-Feb-8-2022.pdf",
        "youtube_id": "OZjT3eE3u-Q",
        "ia_id": None,
    },
    {
        "id": "ocda-012-nava",
        "subject": "Jesse Nava",
        "agency": "Anaheim PD",
        "pdf_path": "/investigation-letters/Nava APD SA 20-021 Final.pdf",
        "youtube_id": "dgD3d_I_wI4",
        "ia_id": None,
    },
    {
        "id": "ocda-013-wong",
        "subject": "Matthew Wong",
        "agency": "Placentia PD",
        "pdf_path": "/wp-content/uploads/2023/01/Wong-Matthew-PPD-SA-21-001941-Final-Letter-with-Signatures.pdf",
        "youtube_id": "Kqf-FJti5A4",
        "ia_id": None,
    },
    {
        "id": "ocda-014-tran",
        "subject": "Matthew-Tuan Ahn Tran",
        "agency": "La Habra PD",
        "pdf_path": "/wp-content/uploads/2022/12/Tran-Matthew-LHPD-S.A.-21-2922-Final-Letter-with-All-Signatures.pdf",
        "youtube_id": "PEqVtC1Yn4k",
        "ia_id": None,
    },
    {
        "id": "ocda-015-baxter",
        "subject": "Cedric Baxter",
        "agency": "Buena Park PD",
        "pdf_path": "/wp-content/uploads/2022/09/Cedric-Baster-21-003557-Final-Signed-8.29.22.pdf",
        "youtube_id": "xJF5_fUBn1c",
        "ia_id": None,
    },
    {
        "id": "ocda-016-salac",
        "subject": "Sunshine Kamille Salac",
        "agency": "OC agency",
        "pdf_path": "/wp-content/uploads/2021/03/Salac-SA-20-015-OIS-Fatal-Report-FINAL-Jan-15-2021.pdf",
        "youtube_id": "-TSzqer7D7Q",
        "ia_id": None,
    },
    {
        "id": "ocda-017-aguirre",
        "subject": "Randolph Aguirre",
        "agency": "La Habra PD",
        "pdf_path": "/wp-content/uploads/2020/12/Aguirre-SA-19-021-Final-Nov-4-2020.pdf",
        "youtube_id": "05fURkLaYcc",
        "ia_id": None,
    },
    {
        "id": "ocda-018-mejia",
        "subject": "Clemente De Garay Mejia",
        "agency": "Tustin PD",
        "pdf_path": "/wp-content/uploads/2024/01/OIS-Clemente-De-Garay-Mejia-correction.pdf",
        "youtube_id": "sDMtt564DWw",
        "ia_id": None,
    },
]


def check_url(url: str, timeout: int = 30) -> tuple[int, int | None]:
    """Return (http_status, content_length_or_None)."""
    req = urllib.request.Request(url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        length = resp.headers.get("Content-Length")
        return resp.status, int(length) if length else None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return -1, None


def download_and_hash(url: str, dest: Path, timeout: int = 60) -> tuple[str, int]:
    """Download file, return (sha256, size)."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (counterpoint-benchmark)")
    urllib.request.urlretrieve(url, dest)
    h = hashlib.sha256()
    with open(dest, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest(), dest.stat().st_size


def main():
    import urllib.parse

    EVIDENCE_DIR.mkdir(exist_ok=True)

    print(f"Checking {len(CASES)} OCDA PDF URLs...\n")

    alive = []
    dead = []

    for case in CASES:
        encoded_path = urllib.parse.quote(case["pdf_path"], safe="/-._~")
        url = OCDA_BASE + encoded_path
        status, size = check_url(url)
        size_str = f" ({size:,} bytes)" if size else ""
        if 200 <= status < 400:
            print(f"  OK  {status} {case['id']}: {case['subject']}{size_str}")
            alive.append((case, url, size))
        else:
            print(f"  FAIL {status} {case['id']}: {case['subject']}  -> {url}")
            dead.append((case, url, status))

    print(f"\n--- Summary ---")
    print(f"  Alive: {len(alive)}/{len(CASES)}")
    print(f"  Dead:  {len(dead)}/{len(CASES)}")

    if dead:
        print(f"\nDead URLs:")
        for case, url, status in dead:
            print(f"  [{status}] {case['id']}: {url}")

    if not alive:
        print("\nNo alive URLs to download.")
        return

    print(f"\nDownloading {len(alive)} PDFs and computing hashes...\n")

    results = []
    for case, url, head_size in alive:
        fname = f"{case['id']}.pdf"
        dest = EVIDENCE_DIR / fname
        try:
            sha, size = download_and_hash(url, dest)
            print(f"  OK  {case['id']}: {size:,} bytes  sha256={sha[:16]}...")
            results.append({
                "case": case,
                "url": url,
                "file_name": fname,
                "sha256": sha,
                "size": size,
            })
        except Exception as e:
            print(f"  FAIL {case['id']}: {e}")

    out_path = BENCHMARK_DIR / "scripts" / "_pdf_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    print(f"Downloaded: {len(results)}/{len(alive)}")


if __name__ == "__main__":
    main()
