"""Precision/recall/F1 of a swiftpick scan at every conflict threshold, from its saved
per-chunk probabilities (no model calls).

    python3 -m pipeline.sweep benchmark/predictions/swiftpick/chunk-probs

Claims are matched to the annotations by text (evaluate.py's Jaccard >= 0.3), never by
claim_id alone: an extractor's own cl-001 is not the annotation's cl-001. Claims taken from
the annotations ("--claims-from gt") keep their ids and match exactly.

A threshold picked on the benchmark itself flatters it, so the script also reports a 2-fold
choice: the threshold that maximizes F1 on the even-numbered scenarios, scored on the odd
ones, and the other way round.

On this benchmark F1 rewards flagging everything: 57.8% of the claims with video are
conflicts, so flag-all scores F1 0.733. Compare systems by AUROC
(benchmark/results/swiftpick-analysis/), not by this curve's best F1.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from .stages.decide import aggregate

ROOT = Path(__file__).resolve().parent.parent / "benchmark"


def _evaluate_module():
    spec = importlib.util.spec_from_file_location("evaluate", ROOT / "scripts" / "evaluate.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    return ev


EV = _evaluate_module()


def predictions(raws: list[dict], threshold: float) -> list[dict]:
    out = []
    for raw in raws:
        claims = aggregate(raw, conflict_threshold=threshold)
        keep_ids = raw.get("claims_from") == "gt"
        out.append({
            "scenario_id": raw["scenario_id"],
            "claims": [{
                "claim_id": c.claim_id if keep_ids else f"pred-{i}",
                "claim_text": c.claim_text,
                "evidence_relationship": c.evidence_relationship,
                "evidence_references": [{"start_seconds": r.start_seconds,
                                         "end_seconds": r.end_seconds}
                                        for r in c.evidence_references],
            } for i, c in enumerate(claims)],
        })
    return out


def score(raws: list[dict], threshold: float, annotations: dict) -> dict:
    res = [EV.evaluate_scenario(p, annotations[p["scenario_id"]])
           for p in predictions(raws, threshold)]
    agg = EV.aggregate_results(res)["aggregate"]
    agg["matched"] = sum(r["claims_matched"] for r in res)
    return agg


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("raw_dir", type=Path)
    p.add_argument("--out", type=Path, help="write the curve as JSON")
    a = p.parse_args()
    raws = [json.load(open(f)) for f in sorted(a.raw_dir.glob("*_raw.json"))]
    annotations = EV.load_annotations()
    raws = [r for r in raws if r["scenario_id"] in annotations]
    grid = [round(t / 100, 2) for t in range(5, 100, 5)]
    curve = {t: score(raws, t, annotations) for t in grid}
    print(f"{len(raws)} scenarios, {curve[grid[0]]['total_claims']} annotated claims, "
          f"{curve[grid[0]]['matched']} matched")
    print(" thr     P      R     F1")
    for t, s in curve.items():
        print(f" {t:.2f}  {s['precision']:.3f}  {s['recall']:.3f}  {s['f1']:.3f}")
    halves = [raws[0::2], raws[1::2]]
    folds = []
    for tune, test in ((halves[0], halves[1]), (halves[1], halves[0])):
        best = max(grid, key=lambda t: score(tune, t, annotations)["f1"])
        s = score(test, best, annotations)
        folds.append({"threshold": best, **{k: s[k] for k in ("precision", "recall", "f1")}})
    print("2-fold (tuned on one half, scored on the other):",
          "; ".join(f"thr {f['threshold']:.2f}: P {f['precision']:.3f} R {f['recall']:.3f} "
                    f"F1 {f['f1']:.3f}" for f in folds))
    if a.out:
        a.out.write_text(json.dumps({"curve": curve, "two_fold": folds}, indent=2))


if __name__ == "__main__":
    main()
