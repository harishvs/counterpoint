# swiftpick-scan analysis (2026-11-08)

Threshold-free scores for the swiftpick-scan runs in `benchmark/predictions/swiftpick-*`
(per-chunk probabilities in each `chunk-probs/`). Needs numpy. Run from anywhere:

```bash
python discrim.py raw "../../predictions/swiftpick-gtclaims/chunk-probs/*_raw.json"   # base rate, flag-all, AUROC
python aggs.py "../../predictions/swiftpick-gtclaims/chunk-probs/*_raw.json"          # AUROC per chunk-combining rule
python ci.py                                                                 # bootstrap CIs, AV vs transcript only
python claim_only.py   # control, needs swiftpick servers on ports 8100-8107; writes claim_only.json
```

Claims are matched to the annotations by text (`evaluate.py`'s Jaccard >= 0.3), with
predicted ids hidden, because `evaluate.py`'s `match_claims` otherwise pairs claims by
`claim_id` alone when half the ids coincide, and an extractor's `cl-001` is not the
annotation's.
