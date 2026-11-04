# Results History

## Run 1: Claude Haiku — Transcript Only (2026-10-28)
- **Pipeline**: claim-first
- **Model**: Claude Haiku 5.5 via Bedrock
- **Input**: transcript only (no video)
- **Scenarios**: 15 | **Claims**: 220

| Metric | Value |
|---|---|
| Precision | 40.0% |
| Recall | 2.8% |
| F1 | 5.3% |
| Abstention | 35.9% |

## Run 2: Nemotron Omni — Claim-First with Video Clips (2026-10-29)
- **Pipeline**: claim-first (keyword retrieval → per-claim clip → verify)
- **Model**: Nemotron 3 Nano Omni 30B-A3B (NVFP4) on L40S
- **Input**: transcript + video clips (only ~30% of claims got clips)
- **Scenarios**: 15 | **Claims**: 220

| Metric | Value |
|---|---|
| Precision | 62.5% |
| Recall | 7.1% |
| F1 | 12.7% |
| Abstention | 21.4% |

**vs Run 1**: P +56%, R +154%, F1 +140%

## Run 3: Nemotron Omni — Video Scan, 15 Scenarios (2026-10-29)
- **Pipeline**: scan (2-min video chunks, all claims per chunk)
- **Model**: Nemotron 3 Nano Omni 30B-A3B (NVFP4) on L40S
- **Input**: full video (chunked) + transcript
- **Scenarios**: 15 | **Claims**: 220

| Metric | Value |
|---|---|
| Precision | 58.1% |
| Recall | 25.5% |
| F1 | 35.5% |
| Abstention | 0.0% |

**vs Run 2**: P -4.4pp, R +18.4pp, F1 +22.8pp (recall tripled)
**vs Run 1**: P +18.1pp, R +22.7pp, F1 +30.2pp (F1 6.7x)

## Run 4: Nemotron Omni — Video Scan, Full Benchmark (2026-11-04)
- **Pipeline**: scan (2-min video chunks, all claims per chunk)
- **Model**: Nemotron 3 Nano Omni 30B-A3B (NVFP4) on L40S
- **Input**: full video (chunked) + transcript
- **Scenarios**: 71 | **Claims**: 1010

| Metric | Value |
|---|---|
| Precision | 61.0% |
| Recall | 24.9% |
| F1 | 35.4% |
| Abstention | 0.0% |

### By Difficulty
| Difficulty | P | R | F1 | n |
|---|---|---|---|---|
| Easy | 38.3% | 23.6% | 29.2% | 532 |
| Medium | 94.5% | 24.3% | 38.7% | 298 |
| Hard | 66.7% | 28.8% | 40.2% | 180 |

### By Discrepancy Type
| Type | P | R | F1 | n |
|---|---|---|---|---|
| sequence_mismatch | 100% | 35.5% | 52.4% | 31 |
| minimization | 100% | 34.7% | 51.5% | 72 |
| omission | 100% | 28.3% | 44.1% | 53 |
| fabrication | 93.3% | 26.4% | 41.2% | 54 |
| temporal_mismatch | 100% | 23.4% | 37.9% | 78 |
| exaggeration | 100% | 21.8% | 35.8% | 78 |
| direct_contradiction | 100% | 20.9% | 34.5% | 208 |
| ambiguous_language | 16.7% | 33.3% | 22.2% | 76 |

### Notes
- AFPD scenarios (SC-019-021, 069-071) matched 0/15 claims — videos not on GPU
- Negative examples (SC-037-046) had some false positives (19 total across 10 scenarios)
- Consistent with Run 3 results at 15-scenario scale
