# Counterpoint Benchmark

A benchmark for evaluating claim-to-evidence review pipelines using publicly
available bodycam footage and authored incident reports with known ground-truth
discrepancies.

## How it works

Video/audio evidence is **not distributed** with this repository. Instead, a
manifest points to stable public URLs (Internet Archive, COPA portal) and
includes SHA-256 hashes for integrity verification.

What this repo contains:
- `manifest.json` — source list with download URLs, hashes, and metadata
- `reports/` — authored incident reports (one per scenario)
- `annotations/` — ground-truth discrepancy annotations (one per scenario)
- `scripts/download.py` — fetches evidence files into `evidence/` (gitignored)
- `scripts/validate.py` — verifies downloaded files against manifest hashes

## Quick start

```bash
# Download all evidence files (~X GB)
python -I scripts/download.py

# Verify integrity
python -I scripts/validate.py

# Download a single scenario
python -I scripts/download.py --scenario sc-001
```

## Scenario design

Each scenario pairs a real public bodycam video with an authored incident report.
The report is written *after* watching the video and deliberately includes a mix of:
- Accurate claims (supported by evidence)
- Discrepant claims (contradicted by evidence)
- Ambiguous claims (insufficient or unclear evidence)
- Claims with no retrievable evidence

Ground truth annotations specify the relationship between each report claim and
the evidence, with timestamps and explanations.

## Directory layout

```
benchmark/
  manifest.json            # evidence sources, URLs, hashes
  reports/
    sc-001_report.txt      # authored incident report
    sc-002_report.txt
  annotations/
    sc-001_annotations.json
    sc-002_annotations.json
  evidence/                # gitignored, populated by download script
    sc-001_bodycam.mp4
    sc-002_bodycam.mp4
  scripts/
    download.py
    validate.py
  schema/
    manifest.schema.json
    annotation.schema.json
    report_template.txt
```

## Limitations

- Authored reports are fictional — they are not real police reports.
- Scenarios test pipeline mechanics, not real-world legal adequacy.
- Video sources may become unavailable (link rot). Hashes allow verification
  if files are obtained through alternative means.
- This is a development benchmark, not a statistically validated evaluation suite.
