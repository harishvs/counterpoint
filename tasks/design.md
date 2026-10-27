# Benchmark Design

## Architecture

```
User runs download.py
        │
        ▼
manifest.json ──→ fetch from public URLs ──→ evidence/ (gitignored)
        │
        ▼
validate.py ──→ SHA-256 check + annotation cross-reference
```

## Data flow for benchmark creation (human workflow)

1. Pick a public bodycam video (OCDA/IA)
2. Watch it, document what happens (ground truth)
3. Write a fictional incident report with deliberate discrepancies
4. Create annotation JSON linking claims to evidence timestamps
5. Add source to manifest.json with URL + hash
6. Run validate.py to check everything links up

## Annotation schema design choices

### Claim types (7)
- spoken_statement, action_description, object_description
- temporal_sequence, location_description, identity_description
- subjective_characterization

### Ground truth relationships (4)
- supported, conflict, ambiguous, no_evidence

### Discrepancy types (9)
- direct_contradiction, omission, sequence_mismatch, temporal_mismatch
- exaggeration, minimization, fabrication, ambiguous_language, none

### Evidence references
- Timestamped (start_seconds, end_seconds)
- Modality tagged (audio, visual, both)
- Include transcript excerpt and/or visual description

### Per-claim difficulty rating
- easy, medium, hard — for stratified metric reporting

## Key decisions made
- Evidence NOT redistributed — URLs + hashes only
- Reports are authored fiction, NOT real police reports
- OCDA DA investigation letters are the primary source (describe bodycam in detail)
- Internet Archive mirrors preferred for link stability
- Synthetic scenarios supplement real data for discrepancy types not in OIS reports
