"""Evaluate model predictions against ground-truth annotations.

Usage:
    python3 -I scripts/evaluate.py predictions/            # evaluate all prediction files in dir
    python3 -I scripts/evaluate.py pred_sc-001.json        # evaluate single file
    python3 -I scripts/evaluate.py predictions/ --out results/  # save results JSON
    python3 -I scripts/evaluate.py predictions/ --iou-threshold 0.5
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent.parent
ANNOTATIONS_DIR = BENCHMARK_DIR / "annotations"


def load_annotations() -> dict[str, dict]:
    """Load all annotations, keyed by scenario_id."""
    annotations = {}
    for f in ANNOTATIONS_DIR.glob("*.json"):
        with open(f) as fh:
            ann = json.load(fh)
        annotations[ann["scenario_id"]] = ann
    return annotations


def load_predictions(path: Path) -> list[dict]:
    """Load prediction file(s) from a path (file or directory)."""
    preds = []
    if path.is_dir():
        for f in sorted(path.glob("*.json")):
            with open(f) as fh:
                preds.append(json.load(fh))
    else:
        with open(path) as fh:
            preds.append(json.load(fh))
    return preds


def compute_iou(pred_start: float, pred_end: float,
                gt_start: float, gt_end: float) -> float:
    """Compute intersection-over-union for two time intervals."""
    intersection = max(0, min(pred_end, gt_end) - max(pred_start, gt_start))
    union = max(pred_end, gt_end) - min(pred_start, gt_start)
    if union <= 0:
        return 0.0
    return intersection / union


def _normalize(text: str) -> set[str]:
    """Normalize text to a set of lowercase words for comparison."""
    import re
    words = re.sub(r"[^a-z0-9 ]", "", text.lower()).split()
    return set(w for w in words if len(w) > 2)


def _text_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two text strings."""
    wa, wb = _normalize(a), _normalize(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def match_claims(gt_claims: list[dict], pred_claims: list[dict],
                 threshold: float = 0.3) -> dict[str, dict | None]:
    """Match ground-truth claims to predictions by claim_id or text similarity.

    Returns dict mapping gt claim_id → best matching prediction (or None).
    """
    gt_by_id = {c["claim_id"]: c for c in gt_claims}
    pred_by_id = {c["claim_id"]: c for c in pred_claims}

    id_hits = sum(1 for cid in gt_by_id if cid in pred_by_id)
    if id_hits >= len(gt_by_id) * 0.5:
        return {cid: pred_by_id.get(cid) for cid in gt_by_id}

    matched = {}
    used_preds = set()

    for gt in gt_claims:
        gt_text = gt.get("claim_text", "")
        best_score = 0.0
        best_pred = None

        for pred in pred_claims:
            pid = id(pred)
            if pid in used_preds:
                continue
            pred_text = pred.get("claim_text", "")
            if not pred_text:
                continue
            score = _text_similarity(gt_text, pred_text)
            if score > best_score:
                best_score = score
                best_pred = pred
                best_pred_id = pid

        if best_pred and best_score >= threshold:
            matched[gt["claim_id"]] = best_pred
            used_preds.add(best_pred_id)
        else:
            matched[gt["claim_id"]] = None

    return matched


def evaluate_scenario(prediction: dict, annotation: dict,
                      iou_threshold: float = 0.3) -> dict:
    """Evaluate a single scenario's predictions against ground truth."""
    gt_claims_list = annotation["claims"]
    pred_claims_list = prediction.get("claims", [])

    claim_matches = match_claims(gt_claims_list, pred_claims_list)
    gt_claims = {c["claim_id"]: c for c in gt_claims_list}

    tp = fp = fn = 0
    abstentions = 0
    retrieval_hits = 0
    retrieval_total = 0
    iou_scores = []
    source_ref_correct = 0
    source_ref_total = 0

    per_claim = []

    for claim_id, gt in gt_claims.items():
        pred = claim_matches.get(claim_id)
        gt_rel = gt["ground_truth_relationship"]
        gt_disc = gt.get("discrepancy_type", "unknown")
        gt_diff = gt.get("difficulty", "unknown")
        gt_type = gt.get("claim_type", "unknown")

        if pred is None:
            if gt_rel == "conflict":
                fn += 1
            per_claim.append({
                "claim_id": claim_id,
                "gt_relationship": gt_rel,
                "pred_relationship": "missing",
                "correct": False,
                "discrepancy_type": gt_disc,
                "difficulty": gt_diff,
                "claim_type": gt_type,
            })
            continue

        pred_rel = pred["evidence_relationship"]

        if pred_rel == "not_assessed":
            abstentions += 1
            if gt_rel == "conflict":
                fn += 1
            per_claim.append({
                "claim_id": claim_id,
                "gt_relationship": gt_rel,
                "pred_relationship": pred_rel,
                "correct": False,
                "abstention": True,
                "discrepancy_type": gt_disc,
                "difficulty": gt_diff,
                "claim_type": gt_type,
            })
            continue

        is_pred_conflict = pred_rel == "potential_conflict"
        is_gt_conflict = gt_rel == "conflict"

        if is_pred_conflict and is_gt_conflict:
            tp += 1
        elif is_pred_conflict and not is_gt_conflict:
            fp += 1
        elif not is_pred_conflict and is_gt_conflict:
            fn += 1

        correct = (is_pred_conflict == is_gt_conflict)
        if gt_rel == "ambiguous":
            correct = pred_rel in ("ambiguous_or_insufficient", "potential_conflict")

        retrieval_status = pred.get("retrieval_status", "not_retrieved")
        if retrieval_status == "retrieved":
            retrieval_hits += 1
        retrieval_total += 1

        gt_refs = gt.get("evidence_references", [])
        pred_refs = pred.get("evidence_references", [])
        if gt_refs and pred_refs:
            gt_ref = gt_refs[0]
            pred_ref = pred_refs[0]
            gt_start = gt_ref.get("start_seconds")
            gt_end = gt_ref.get("end_seconds")
            pred_start = pred_ref.get("start_seconds")
            pred_end = pred_ref.get("end_seconds")

            if all(v is not None for v in [gt_start, gt_end, pred_start, pred_end]):
                iou = compute_iou(pred_start, pred_end, gt_start, gt_end)
                iou_scores.append(iou)
                source_ref_total += 1
                if iou >= iou_threshold:
                    source_ref_correct += 1

        per_claim.append({
            "claim_id": claim_id,
            "gt_relationship": gt_rel,
            "pred_relationship": pred_rel,
            "correct": correct,
            "discrepancy_type": gt_disc,
            "difficulty": gt_diff,
            "claim_type": gt_type,
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    retrieval_recall = retrieval_hits / retrieval_total if retrieval_total > 0 else 0.0
    mean_iou = sum(iou_scores) / len(iou_scores) if iou_scores else None
    source_ref_acc = source_ref_correct / source_ref_total if source_ref_total > 0 else None
    abstention_rate = abstentions / len(gt_claims) if gt_claims else 0.0

    matched_count = sum(1 for v in claim_matches.values() if v is not None)

    return {
        "scenario_id": annotation["scenario_id"],
        "model": prediction.get("model", "unknown"),
        "pipeline": prediction.get("pipeline", "unknown"),
        "counts": {"tp": tp, "fp": fp, "fn": fn, "total": len(gt_claims)},
        "claims_matched": matched_count,
        "claims_gt": len(gt_claims),
        "claims_predicted": len(pred_claims_list),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "retrieval_recall": round(retrieval_recall, 4),
        "temporal_iou_mean": round(mean_iou, 4) if mean_iou is not None else None,
        "source_ref_accuracy": round(source_ref_acc, 4) if source_ref_acc is not None else None,
        "abstention_rate": round(abstention_rate, 4),
        "iou_scores_count": len(iou_scores),
        "per_claim": per_claim,
        "systems": {
            "processing_time_seconds": prediction.get("processing_time_seconds"),
            "total_tokens": prediction.get("total_tokens"),
            "total_api_calls": prediction.get("total_api_calls"),
        },
    }


def aggregate_results(scenario_results: list[dict]) -> dict:
    """Aggregate metrics across scenarios with stratified breakdowns."""
    all_claims = []
    for sr in scenario_results:
        all_claims.extend(sr["per_claim"])

    total_tp = sum(r["counts"]["tp"] for r in scenario_results)
    total_fp = sum(r["counts"]["fp"] for r in scenario_results)
    total_fn = sum(r["counts"]["fn"] for r in scenario_results)
    total_claims = sum(r["counts"]["total"] for r in scenario_results)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    iou_vals = []
    for sr in scenario_results:
        if sr["temporal_iou_mean"] is not None:
            iou_vals.extend([sr["temporal_iou_mean"]] * sr["iou_scores_count"])

    def stratify(claims: list[dict], key: str) -> dict:
        groups = defaultdict(list)
        for c in claims:
            groups[c.get(key, "unknown")].append(c)

        result = {}
        for group_name, group_claims in sorted(groups.items()):
            g_tp = sum(1 for c in group_claims if c["gt_relationship"] == "conflict" and c["pred_relationship"] == "potential_conflict")
            g_fp = sum(1 for c in group_claims if c["gt_relationship"] != "conflict" and c["pred_relationship"] == "potential_conflict")
            g_fn = sum(1 for c in group_claims if c["gt_relationship"] == "conflict" and c["pred_relationship"] != "potential_conflict")
            g_prec = g_tp / (g_tp + g_fp) if (g_tp + g_fp) > 0 else 0.0
            g_rec = g_tp / (g_tp + g_fn) if (g_tp + g_fn) > 0 else 0.0
            g_f1 = 2 * g_prec * g_rec / (g_prec + g_rec) if (g_prec + g_rec) > 0 else 0.0
            result[group_name] = {
                "count": len(group_claims),
                "precision": round(g_prec, 4),
                "recall": round(g_rec, 4),
                "f1": round(g_f1, 4),
            }
        return result

    confusion = defaultdict(lambda: defaultdict(int))
    for c in all_claims:
        confusion[c["gt_relationship"]][c["pred_relationship"]] += 1

    return {
        "aggregate": {
            "total_claims": total_claims,
            "total_scenarios": len(scenario_results),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "temporal_iou_mean": round(sum(iou_vals) / len(iou_vals), 4) if iou_vals else None,
            "abstention_rate": round(
                sum(1 for c in all_claims if c.get("abstention")) / len(all_claims), 4
            ) if all_claims else 0.0,
        },
        "by_difficulty": stratify(all_claims, "difficulty"),
        "by_discrepancy_type": stratify(all_claims, "discrepancy_type"),
        "by_claim_type": stratify(all_claims, "claim_type"),
        "confusion_matrix": {k: dict(v) for k, v in confusion.items()},
    }


def print_summary(agg: dict, scenario_results: list[dict]):
    """Print human-readable summary."""
    a = agg["aggregate"]
    print(f"\n{'='*60}")
    print(f"  EVALUATION RESULTS")
    print(f"  {a['total_scenarios']} scenarios, {a['total_claims']} claims")
    print(f"{'='*60}")
    print(f"  Precision:       {a['precision']:.1%}")
    print(f"  Recall:          {a['recall']:.1%}")
    print(f"  F1:              {a['f1']:.1%}")
    if a["temporal_iou_mean"] is not None:
        print(f"  Temporal IoU:    {a['temporal_iou_mean']:.1%}")
    print(f"  Abstention rate: {a['abstention_rate']:.1%}")

    print(f"\n  By difficulty:")
    for diff in ["easy", "medium", "hard"]:
        if diff in agg["by_difficulty"]:
            d = agg["by_difficulty"][diff]
            print(f"    {diff:8s}  P={d['precision']:.1%}  R={d['recall']:.1%}  F1={d['f1']:.1%}  (n={d['count']})")

    print(f"\n  By discrepancy type:")
    for dt, d in sorted(agg["by_discrepancy_type"].items(), key=lambda x: -x[1]["count"]):
        if dt == "none":
            continue
        print(f"    {dt:25s}  P={d['precision']:.1%}  R={d['recall']:.1%}  F1={d['f1']:.1%}  (n={d['count']})")

    print(f"\n  Confusion matrix (rows=ground truth, cols=predicted):")
    pred_labels = sorted(set(
        p for row in agg["confusion_matrix"].values() for p in row
    ))
    header = "  {:>12s}".format("") + "".join(f"  {p[:12]:>12s}" for p in pred_labels)
    print(header)
    for gt_label in ["conflict", "supported", "ambiguous", "no_evidence"]:
        if gt_label not in agg["confusion_matrix"]:
            continue
        row = agg["confusion_matrix"][gt_label]
        cells = "".join(f"  {row.get(p, 0):>12d}" for p in pred_labels)
        print(f"  {gt_label:>12s}{cells}")

    print(f"\n  Per-scenario:")
    for sr in scenario_results:
        match_info = f"matched={sr.get('claims_matched', '?')}/{sr.get('claims_gt', '?')}"
        print(f"    {sr['scenario_id']}  P={sr['precision']:.1%}  R={sr['recall']:.1%}  F1={sr['f1']:.1%}  "
              f"(tp={sr['counts']['tp']} fp={sr['counts']['fp']} fn={sr['counts']['fn']})  {match_info}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate predictions against ground truth")
    parser.add_argument("predictions", type=Path, help="Prediction file or directory")
    parser.add_argument("--out", type=Path, help="Output directory for results JSON")
    parser.add_argument("--iou-threshold", type=float, default=0.3,
                        help="IoU threshold for source-reference correctness (default: 0.3)")
    args = parser.parse_args()

    annotations = load_annotations()
    predictions = load_predictions(args.predictions)

    if not predictions:
        print("No prediction files found.")
        sys.exit(1)

    scenario_results = []
    for pred in predictions:
        sid = pred["scenario_id"]
        if sid not in annotations:
            print(f"  WARNING: no annotation for {sid}, skipping")
            continue
        result = evaluate_scenario(pred, annotations[sid], iou_threshold=args.iou_threshold)
        scenario_results.append(result)

    if not scenario_results:
        print("No matching scenarios found.")
        sys.exit(1)

    agg = aggregate_results(scenario_results)
    print_summary(agg, scenario_results)

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        model = scenario_results[0].get("model", "unknown").replace("/", "_")
        pipeline = scenario_results[0].get("pipeline", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = args.out / f"{model}_{pipeline}_{ts}.json"
        full_results = {
            "evaluated_at": datetime.now().isoformat(),
            "iou_threshold": args.iou_threshold,
            "aggregate": agg,
            "scenarios": scenario_results,
        }
        with open(out_path, "w") as f:
            json.dump(full_results, f, indent=2)
        print(f"  Results saved to {out_path}")


if __name__ == "__main__":
    main()
