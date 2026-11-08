"""Base rates, the flag-everything baseline, and AUROC of a claim score vs GT conflict (text-matched claims)."""
import glob, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from pipeline.sweep import EV
anns = EV.load_annotations()


def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int); pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg): return float("nan")
    return float(((pos[:, None] > neg[None]).sum() + 0.5 * (pos[:, None] == neg[None]).sum()) / (len(pos) * len(neg)))


def gt_pairs(sid, pred_claims, keep_ids):
    preds = pred_claims if keep_ids else [{**c, "claim_id": f"pred-{i}"} for i, c in enumerate(pred_claims)]
    m = EV.match_claims(anns[sid]["claims"], preds)
    return [(g, m[g["claim_id"]]) for g in anns[sid]["claims"]]


def main(mode, path):
    ys, ss, unmatched_conf = [], [], 0
    for f in sorted(glob.glob(path)):
        d = json.load(open(f))
        if mode == "raw":
            ok = [c for c in d["chunks"] if "probs" in c]
            claims = [{"claim_id": c["claim_id"], "claim_text": c["claim_text"],
                       "score": max(ch["probs"][c["claim_id"]]["potential_conflict"] for ch in ok)} for c in d["claims"]]
            pairs = gt_pairs(d["scenario_id"], claims, d.get("claims_from") == "gt")
        else:
            claims = [{**c, "score": float(c["evidence_relationship"] == "potential_conflict")} for c in d["claims"]]
            pairs = gt_pairs(d["scenario_id"], claims, False)
        for g, p in pairs:
            if p is None:
                unmatched_conf += g["ground_truth_relationship"] == "conflict"; continue
            ys.append(int(g["ground_truth_relationship"] == "conflict")); ss.append(p["score"])
    y = np.array(ys); r = y.sum() / (y.sum() + unmatched_conf)
    print(f"matched {len(y)}, conflict rate among matched {y.mean():.3f}; flag-everything P {y.mean():.3f} "
          f"R {r:.3f} F1 {2*y.mean()*r/(y.mean()+r):.3f}; AUROC {auroc(ss, y):.3f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
