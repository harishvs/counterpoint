# Counterpoint

Source-grounded multimodal evidence review for public defenders.

An open-source AI application that helps under-resourced public defenders identify potential discrepancies between police incident reports and supporting evidence (body-camera footage, 911 calls, photographs, and other case materials).

## How it works

1. Extract factual claims from an incident report.
2. Locate relevant evidence passages and audiovisual segments.
3. Compare each claim with retrieved evidence.
4. Flag potentially conflicting statements or observations.
5. Provide original-source references and timestamps for attorney verification.

This assists evidence review. It does not determine guilt, assess misconduct, or replace attorney judgment.

## Repository structure

```
counterpoint/
  benchmark/              # Redistributable evaluation dataset
    manifest.json         # Evidence source URLs and integrity hashes
    schema/               # JSON schemas for annotations and manifest
    scripts/              # Download and validation utilities
    reports/              # Authored incident reports (future)
    annotations/          # Ground-truth discrepancy annotations (future)
    evidence/             # Downloaded files (gitignored)
  tasks/                  # Project planning and progress tracking
```

## Benchmark

The benchmark pairs real public bodycam footage with authored incident reports containing known ground-truth discrepancies. Evidence files are not distributed — the manifest provides download URLs to publicly available sources (OCDA, Internet Archive, YouTube) with SHA-256 hashes for integrity verification.

```bash
cd benchmark

# Download all evidence files
python3 -I scripts/download.py

# Verify integrity
python3 -I scripts/validate.py

# List sources without downloading
python3 -I scripts/download.py --list
```

See [benchmark/README.md](benchmark/README.md) for details on scenario design and annotation format.

## Status

Early development. The benchmark scaffold and 16 verified OCDA source PDFs are in place. Video source verification and annotation authoring are in progress.

## License

TBD
