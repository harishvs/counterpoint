"""AUROC of several per-claim scores built from per-chunk probabilities (exploratory)."""
import glob, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[3])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from discrim import auroc, gt_pairs  # noqa
def scores(ch):
    c = np.array([x["potential_conflict"] for x in ch]); s = np.array([x["supported"] for x in ch]); a = np.array([x["ambiguous_or_insufficient"] for x in ch])
    d = int(np.argmin(a))
    return {"max P(conflict)": c.max(), "mean P(conflict)": c.mean(), "max P(conf)-P(sup)": (c - s).max(),
            "P(conf) at most decisive chunk": c[d], "conf share at most decisive": c[d] / (c[d] + s[d]),
            "-max P(supported)": -s.max(), "top-3 mean P(conflict)": np.sort(c)[-3:].mean()}
ys, rows = [], []
by = {}
for f in sorted(glob.glob(sys.argv[1])):
    d = json.load(open(f)); ok = [c for c in d["chunks"] if "probs" in c]
    claims = [{"claim_id": c["claim_id"], "claim_text": c["claim_text"], "s": scores([ch["probs"][c["claim_id"]] for ch in ok])} for c in d["claims"]]
    for g, p in gt_pairs(d["scenario_id"], claims, d.get("claims_from") == "gt"):
        if p is None: continue
        ys.append(int(g["ground_truth_relationship"] == "conflict")); rows.append(p["s"])
        by.setdefault(g.get("difficulty"), []).append((ys[-1], p["s"]["max P(conflict)"]))
for k in rows[0]:
    print(f"{k:>32}: AUROC {auroc([r[k] for r in rows], ys):.3f}")
print("by difficulty (max P(conflict)):", {k: round(auroc([s for _, s in v], [y for y, _ in v]), 3) for k, v in by.items()})
