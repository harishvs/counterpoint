# Requirements: Counterpoint Benchmark Dataset

## Goal
Build a redistributable benchmark for evaluating claim-to-evidence review pipelines,
using publicly available bodycam footage paired with authored incident reports
containing known ground-truth discrepancies.

## Key design decision
Evidence files are NOT distributed. The repo contains download URLs pointing to
public sources (Internet Archive, YouTube, OCDA website). A download script
fetches them locally. SHA-256 hashes verify integrity.

## Data sources identified

### Primary: Orange County DA OIS Reports (BEST SOURCE)
- 229 total OIS investigation reports at ocdistrictattorney.gov
- 18 verified cases with BOTH a PDF investigation letter AND bodycam YouTube video
- 12 of those 18 also mirrored on Internet Archive for link stability
- DA letters describe bodycam content in detail — ideal for claim extraction
- Covers officer-involved shooting scenarios

### Secondary: American Fork PD (Internet Archive)
- URL: https://archive.org/details/reckless-ben-BAM-bodycam-docs
- 21 bodycam videos + 6 police report PDFs (incident reports, booking sheets, probable cause)
- Covers trespass, harassment, drug search — different from OIS
- Single case/subject, limited diversity

### Tertiary: Chicago COPA
- 31,000+ cases but only PDFs on case portal — no video hosted there
- FSR PDFs useful as format references for realistic report structure

### Also noted
- LVMPD Oct 1 releases (Internet Archive) — single mass-casualty event
- LA County DA OIS reports — 28 PDFs but no paired video on DA site
- HuggingFace synthetic UK police reports (30 entries, too small)

## Benchmark composition plan
- 10-15 OCDA cases (real DA reports + real bodycam)
- 3-5 American Fork PD cases (different incident types)
- 5-10 authored synthetic scenarios (written against real videos to test
  discrepancy types not covered by real reports: consent/refusal, event
  ordering, fabrication, ambiguous evidence)

## Acceptance criteria
- `python -I scripts/download.py` fetches all evidence files
- `python -I scripts/validate.py` verifies hashes and cross-checks annotations
- Each scenario has: evidence file, authored report, ground-truth annotation
- Annotations follow the JSON schema in benchmark/schema/annotation.schema.json
