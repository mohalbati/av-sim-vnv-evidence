"""Fusing simulated and real results: how many real paired scenarios does simulation save?

Uses the per-vehicle results of av-sim-credibility/scripts/womd_pilot.py (womd_agents_<setting>.csv: real and simulated
outcomes for the same 13,195 vehicles). These files are derived from the Waymo Open Motion Dataset and are not
redistributed; point --agents-dir at the folder where womd_pilot.py wrote them. Because WOMD gives the real outcome for every vehicle, the full-data real rate is the "truth";
we then pretend only n vehicles have a real label (random subset) and the rest only a simulated one, and check each
estimator's error, interval width and coverage over many random subsets.

Run:  python scripts/fusion_study.py --agents-dir ../av-sim-credibility/results   ->  results/fusion_*.csv, results/fusion_study.json
"""
import sys, csv, json, pathlib, argparse
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from simfusion import fusion

RES = ROOT / "results"; RES.mkdir(exist_ok=True)
ap = argparse.ArgumentParser(); ap.add_argument("--agents-dir", default=str(ROOT.parent / "av-sim-credibility" / "results"))
AGENTS = pathlib.Path(ap.parse_args().agents_dir).expanduser()
SETTINGS_NEEDED = ["idm_cautious", "idm", "constant_speed"]
_missing = [f"womd_agents_{s}.csv" for s in SETTINGS_NEEDED if not (AGENTS / f"womd_agents_{s}.csv").exists()]
if _missing:
    sys.exit(f"Per-vehicle inputs not found in {AGENTS}: {', '.join(_missing)}.\n"
             "They are derived from the Waymo Open Motion Dataset and are not redistributed. Create them with\n"
             "av-sim-credibility/scripts/womd_pilot.py (needs Waymax and dataset access), then pass --agents-dir.\n"
             "The aggregate results in results/ already rebuild every table and figure: python scripts/make_figures.py")
SETTINGS = ["idm_cautious", "idm", "constant_speed"]
FAMS = ["car_following", "lane_change", "intersection", "vru_interaction"]
TAU = 1.5
NS = [100, 250, 500, 1000, 2000]
REPS = 1000
rng = np.random.default_rng(2026)


def load(setting):
    rows = list(csv.DictReader(open(AGENTS / f"womd_agents_{setting}.csv")))
    fam = np.array([r["family"] for r in rows])
    rt = np.array([float(r["real_ttc"]) for r in rows]); st = np.array([float(r["sim_ttc"]) for r in rows])
    rc = np.array([r["real_collision"] == "True" for r in rows], float); sc = np.array([r["sim_collision"] == "True" for r in rows], float)
    return fam, {"conflict": ((rt < TAU).astype(float), (st < TAU).astype(float)), "collision": (rc, sc)}


def study(y, s, n):
    N = y.size; truth = y.mean(); out = {k: {"err": [], "w": [], "cov": []} for k in ("classical", "sim_only", "ppi", "ppi_pp")}
    so = fusion.sim_only(s)
    for _ in range(REPS):
        idx = rng.permutation(N); lab, unl = idx[:n], idx[n:]
        res = {"classical": fusion.classical(y[lab]), "sim_only": so,
               "ppi": fusion.ppi(y[lab], s[lab], s[unl]), "ppi_pp": fusion.ppi_pp(y[lab], s[lab], s[unl])}
        for k, r in res.items():
            out[k]["err"].append(r["est"] - truth); out[k]["w"].append(r["hi"] - r["lo"]); out[k]["cov"].append(r["lo"] <= truth <= r["hi"])
    return truth, {k: {"bias": float(np.mean(v["err"])), "rmse": float(np.sqrt(np.mean(np.square(v["err"])))),
                       "width": float(np.mean(v["w"])), "coverage": float(np.mean(v["cov"]))} for k, v in out.items()}


rows = []
for setting in SETTINGS:
    fam, targets = load(setting)
    for target, (y_all, s_all) in targets.items():
        for group in ["POOLED"] + FAMS:
            m = np.ones(fam.size, bool) if group == "POOLED" else fam == group
            y, s = y_all[m], s_all[m]
            rho = float(np.corrcoef(y, s)[0, 1]) if y.std() > 0 and s.std() > 0 else float("nan")
            for n in NS:
                if n >= 0.5 * y.size or (group != "POOLED" and n not in (250, 500)):
                    continue
                truth, r = study(y, s, n)
                gain = (r["classical"]["rmse"] / r["ppi_pp"]["rmse"]) ** 2
                rows.append({"setting": setting, "target": target, "group": group, "N": int(y.size), "n_real": n,
                             "truth": truth, "sim_rate": float(s.mean()), "corr": rho,
                             **{f"{k}_{q}": r[k][q] for k in r for q in ("bias", "rmse", "width", "coverage")},
                             "real_units_equivalent_gain": gain})
            print(f"{setting:<15}{target:<10}{group:<16} N={y.size:<6} real {y.mean():.4f} sim {s.mean():.4f} corr {rho:.2f}")

keys = list(rows[0].keys())
with open(RES / "fusion_study.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

# ---------- hierarchical (partial pooling) of per-family tail ratios, real-data ----------
hier = []
for setting in ["idm_cautious", "idm"]:
    fam, targets = load(setting); y_all, s_all = targets["conflict"]
    lr, se, ns = [], [], []
    for g in FAMS:
        m = fam == g; y, s = y_all[m], s_all[m]
        ky, ks, n = y.sum(), s.sum(), y.size
        lr.append(np.log((ks + 0.5) / (ky + 0.5)))
        se.append(np.sqrt(1 / (ks + 0.5) + 1 / (ky + 0.5)))      # delta-method SE of a log rate ratio
        ns.append(n)
    h = fusion.hierarchical_log_ratio(lr, se)
    for g, l, e, p, ps, sh in zip(FAMS, lr, se, h["pooled"], h["pooled_se"], h["shrink"]):
        hier.append({"setting": setting, "family": g, "R_raw": float(np.exp(l)), "se_log": float(e),
                     "R_pooled": float(np.exp(p)), "R_pooled_lo": float(np.exp(p - 1.96 * ps)), "R_pooled_hi": float(np.exp(p + 1.96 * ps)),
                     "shrink_weight_on_family": float(sh), "R_overall": float(np.exp(h["mu"])), "tau_between_families": float(h["tau"])})
with open(RES / "fusion_hierarchical.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(hier[0].keys())); w.writeheader(); w.writerows(hier)

# ---------- synthetic sweep: how much per-unit agreement does simulation need before it saves real data? ----------
from scipy.stats import norm
syn = []
N_SYN, N_LAB, P = 13195, 500, 0.04
for rl in [0.0, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.98]:
    z = rng.standard_normal((N_SYN, 2)); z2 = rl * z[:, 0] + np.sqrt(1 - rl ** 2) * z[:, 1]
    y = (z[:, 0] < norm.ppf(P)).astype(float); s = (z2 < norm.ppf(P)).astype(float)
    truth, r = study(y, s, N_LAB)
    syn.append({"latent_corr": rl, "corr": float(np.corrcoef(y, s)[0, 1]), "truth": truth,
                "gain": (r["classical"]["rmse"] / r["ppi_pp"]["rmse"]) ** 2, "ppi_pp_coverage": r["ppi_pp"]["coverage"]})
with open(RES / "fusion_synthetic_sweep.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(syn[0].keys())); w.writeheader(); w.writerows(syn)
print("synthetic sweep:", [(round(d["corr"], 2), round(d["gain"], 2)) for d in syn])

json.dump({"tau": TAU, "reps": REPS, "rows": rows, "hierarchical": hier}, open(RES / "fusion_study.json", "w"), indent=1, default=float)
print("wrote results/fusion_study.csv, fusion_hierarchical.csv, fusion_synthetic_sweep.csv, fusion_study.json (figures: scripts/make_figures.py)")
