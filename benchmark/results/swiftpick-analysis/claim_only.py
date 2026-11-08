"""Control: each annotated claim asked with no evidence at all (empty state)."""
import glob, json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[3])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.schemas import ExtractedClaim
from pipeline.stages.decide import SwiftpickClient, _questions
from discrim import auroc, anns
have = {f.split("/")[-1].split("_")[0] for f in glob.glob(str(Path(__file__).resolve().parents[2] / "predictions") + "/swiftpick-gtclaims/chunk-probs/*.json")}
sids = sorted(s for s in anns if s in have)
def one(i_sid):
    i, sid = i_sid
    cl = [ExtractedClaim(c["claim_id"], c["claim_text"], "") for c in anns[sid]["claims"]]
    out = SwiftpickClient(f"http://localhost:810{i % 8}").ask("No evidence is attached.", _questions(cl))
    return sid, {k: v["probabilities"] for k, v in out["answers"].items()}
with ThreadPoolExecutor(8) as ex:
    res = dict(ex.map(one, enumerate(sids)))
json.dump(res, open(str(Path(__file__).resolve().parent / "claim_only.json"), "w"))
ys, ss, amb = [], [], []
for sid, pr in res.items():
    for c in anns[sid]["claims"]:
        ys.append(int(c["ground_truth_relationship"] == "conflict")); ss.append(pr[c["claim_id"]]["potential_conflict"]); amb.append(pr[c["claim_id"]]["ambiguous_or_insufficient"])
print(f"claim-only: {len(ys)} claims, AUROC of P(conflict) {auroc(ss, ys):.3f}; mean P(ambiguous) {sum(amb)/len(amb):.3f}")
