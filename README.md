# Counterpoint

Source-grounded multimodal evidence review for public defenders.

An open-source AI application that helps under-resourced public defenders identify potential discrepancies between police incident reports and supporting evidence (body-camera footage, 911 calls, photographs, and other case materials).

## How it works

1. **Extract** factual claims from an incident report.
2. **Retrieve** relevant evidence passages and audiovisual segments for each claim.
3. **Verify** each claim against the retrieved evidence.
4. **Flag** potentially conflicting statements with source references and timestamps.

This assists evidence review. It does not determine guilt, assess misconduct, or replace attorney judgment.

## Repository structure

```
counterpoint/
  benchmark/                # Evaluation dataset
    manifest.json           # 32 evidence sources (16 PDFs + 16 videos)
    reports/                # 15 authored incident reports with planted discrepancies
    annotations/            # 220 ground-truth claims with labels and timestamps
    schema/                 # JSON schemas (annotation, manifest, prediction)
    scripts/
      download.py           # Fetch evidence files (yt-dlp for YouTube, urllib for IA)
      validate.py           # Verify hashes and cross-check annotations
      evaluate.py           # Score predictions: precision, recall, F1, IoU
      pull_transcripts.py   # Extract YouTube auto-captions as timestamped JSON
      map_timestamps.py     # Auto-map transcript timestamps to annotation claims
    predictions/            # Model output files
    results/                # Evaluation results
  pipeline/                 # Claim-to-evidence review pipeline
    run.py                  # CLI: run pipeline on benchmark scenarios
    schemas.py              # Data models (claims, findings, predictions)
    config.py               # Model endpoint and pipeline configuration
    stages/
      extract.py            # Report → atomic factual claims
      retrieve.py           # Claim + transcript → relevant evidence segments
      verify.py             # Claim + evidence → supported/conflict/ambiguous
    adapters/
      base.py               # Abstract model adapter interface
      claude.py             # Claude via Anthropic API or AWS Bedrock
      nemotron.py           # NVIDIA Nemotron Omni (stub)
  tasks/                    # Project planning and progress tracking
```

## Benchmark

15 scenarios, each pairing a real OCDA bodycam video with a fictional incident report containing known discrepancies. 220 ground-truth claims labeled as conflict (64%), supported (31%), or ambiguous (5%).

| Metric | Count |
|---|---|
| Scenarios | 15 |
| Total claims | 220 |
| Discrepancy types | 9 (contradiction, fabrication, omission, exaggeration, minimization, ...) |
| Difficulty levels | easy (53%), medium (30%), hard (17%) |

Evidence files are not distributed — the manifest provides download URLs to publicly available sources (OCDA, Internet Archive, YouTube) with SHA-256 hashes for integrity verification.

### Setup

```bash
cd benchmark

# Download evidence (age-restricted YouTube videos need Firefox cookies)
python3 -I scripts/download.py --cookies-from-browser firefox

# Pull YouTube transcripts
python3 -I scripts/pull_transcripts.py --cookies-from-browser firefox

# Auto-map timestamps to claims
python3 -I scripts/map_timestamps.py --apply

# Verify everything
python3 -I scripts/validate.py
```

## Pipeline

Three-stage claim-first architecture with swappable model adapters.

```bash
# Install dependencies
pip install anthropic boto3

# Run claim-first pipeline on a scenario (uses Bedrock by default)
python3 -m pipeline.run --scenario sc-001

# Run single-pass baseline for comparison
python3 -m pipeline.run --scenario sc-001 --pipeline single-pass

# Run all scenarios
python3 -m pipeline.run --all

# Evaluate predictions against ground truth
python3 -I benchmark/scripts/evaluate.py benchmark/predictions/
```

### Baselines

| Baseline | Description |
|---|---|
| `claim-first` | Extract claims → retrieve evidence per claim → verify each (proposed pipeline) |
| `single-pass` | Give model the full report + transcript in one shot |
| `transcript-only` | Text-only comparison using transcripts (planned) |

### Evaluation metrics

- **Precision/Recall/F1** for conflict detection, stratified by difficulty and discrepancy type
- **Temporal IoU** for source-reference accuracy
- **Retrieval recall** and **abstention rates**
- **Systems metrics**: processing time, tokens, API calls per scenario

## Status

Active development. Benchmark complete, pipeline functional, first evaluation runs done. Next: run baselines with transcripts, research Nemotron Omni for on-premises deployment.

## License

TBD
