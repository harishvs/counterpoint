import glob, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from discrim import auroc, anns
def decisive(path):
    out = {}
    for f in glob.glob(path):
        d = json.load(open(f)); ok = [c for c in d["chunks"] if "probs" in c]
        for c in d["claims"]:
            ch = [x["probs"][c["claim_id"]] for x in ok]; i = int(np.argmin([x["ambiguous_or_insufficient"] for x in ch]))
            out[(d["scenario_id"], c["claim_id"])] = ch[i]["potential_conflict"]
    return out
R = str(Path(__file__).resolve().parents[2] / "predictions") + "/swiftpick-{}/chunk-probs/*_raw.json"
av, tx = decisive(R.format("gtclaims")), decisive(R.format("gt-transcript-only"))
keys = sorted(av); y = {k: int(c["ground_truth_relationship"] == "conflict") for s in anns for c in anns[s]["claims"] for k in [(s, c["claim_id"])]}
sids = sorted({k[0] for k in keys}); byS = {s: [k for k in keys if k[0] == s] for s in sids}
rng = np.random.default_rng(0); bs = []
for _ in range(2000):
    ks = [k for s in rng.choice(sids, len(sids)) for k in byS[s]]
    yy = [y[k] for k in ks]; a, t = auroc([av[k] for k in ks], yy), auroc([tx[k] for k in ks], yy); bs.append((a, t, a - t))
bs = np.array(bs); yy = [y[k] for k in keys]
print(f"video+audio+transcript {auroc([av[k] for k in keys], yy):.3f} ({np.percentile(bs[:,0],2.5):.3f}-{np.percentile(bs[:,0],97.5):.3f}); "
      f"transcript only {auroc([tx[k] for k in keys], yy):.3f} ({np.percentile(bs[:,1],2.5):.3f}-{np.percentile(bs[:,1],97.5):.3f}); "
      f"difference {np.percentile(bs[:,2],2.5):+.3f} to {np.percentile(bs[:,2],97.5):+.3f}")
