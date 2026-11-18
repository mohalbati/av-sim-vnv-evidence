"""Figures for docs/technical_report.md from results/fusion_study.csv and results/fusion_synthetic_sweep.csv.

Runs without the dataset.
Run: python scripts/make_figures.py
"""
import csv, pathlib
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "docs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.spines.top": False, "axes.spines.right": False})
GREY, BLUE, ORANGE, RUST = "#8a8f98", "#2F6DB5", "#E0A33A", "#B4561C"
SETTINGS = ["idm_cautious", "idm", "constant_speed"]
rows = [{k: (float(v) if k not in ("setting", "target", "group") else v) for k, v in r.items()}
        for r in csv.DictReader(open(RES / "fusion_study.csv"))]
sweep = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(open(RES / "fusion_synthetic_sweep.csv"))]


def pick(setting, target, group="POOLED"):
    return sorted([r for r in rows if r["setting"] == setting and r["target"] == target and r["group"] == group], key=lambda r: r["n_real"])


def save(fig, name):
    fig.savefig(FIG / name, dpi=170, bbox_inches="tight"); plt.close(fig); print("wrote docs/figures/" + name)


# 1. error of each estimator vs number of real paired vehicles (conflict rate, pooled)
fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
for ax, s in zip(axes, SETTINGS):
    rs = pick(s, "conflict"); n = [r["n_real"] for r in rs]
    ax.plot(n, [r["classical_rmse"] for r in rs], "o-", color=GREY, label="real only")
    ax.plot(n, [r["ppi_rmse"] for r in rs], "s-", color=ORANGE, label="PPI")
    ax.plot(n, [r["ppi_pp_rmse"] for r in rs], "^--", color=BLUE, label="PPI++")
    ax.axhline(rs[0]["sim_only_rmse"], color=RUST, ls=":", label="simulation only")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("real paired vehicles n")
    ax.set_title(f"{s}  (ρ = {rs[0]['corr']:.2f})", loc="left", fontsize=9.5)
axes[0].set_ylabel("RMSE of the conflict-rate estimate"); axes[0].legend(frameon=False, fontsize=8)
save(fig, "fusion_rmse.png")

# 2. gain vs per-vehicle correlation
fig, ax = plt.subplots(figsize=(6.2, 3.6))
c = np.linspace(0, 0.9, 100); ax.plot(c, 1 / (1 - c ** 2), color="k", lw=0.8, label="1 / (1 − ρ²)")
ax.scatter([r["corr"] for r in sweep], [r["gain"] for r in sweep], marker="D", s=26, color=GREY, label="synthetic pairs, planted agreement")
for s, mk, col in zip(SETTINGS, ("o", "s", "^"), (BLUE, ORANGE, RUST)):
    p = [r for r in rows if r["setting"] == s and r["target"] == "conflict" and r["n_real"] == 500]
    ax.scatter([r["corr"] for r in p], [r["real_units_equivalent_gain"] for r in p], marker=mk, s=34, color=col, label=f"{s} (pooled and by family)")
ax.set_xlabel("per-vehicle correlation ρ of recorded and simulated close call"); ax.set_ylabel("gain (real-data equivalent)")
ax.set_ylim(0.8, 5.5); ax.legend(frameon=False, fontsize=7.8)
save(fig, "fusion_gain.png")

# 3. interval coverage vs n, conflict and collision targets (pooled)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.2), sharey=True)
for ax, t in zip(axes, ("conflict", "collision")):
    for s, col in zip(SETTINGS, (BLUE, ORANGE, RUST)):
        rs = pick(s, t); n = [r["n_real"] for r in rs]
        ax.plot(n, [r["ppi_pp_coverage"] for r in rs], "o-", color=col, label=f"PPI++, {s}")
        ax.plot(n, [r["classical_coverage"] for r in rs], ":", color=col, alpha=0.7)
    ax.axhline(0.95, color="k", lw=0.7); ax.set_xscale("log"); ax.set_xlabel("real paired vehicles n")
    ax.set_title(f"{t} rate (recorded {100 * rs[0]['truth']:.2f}%)", loc="left", fontsize=9.5)
axes[0].set_ylabel("coverage of nominal 95% interval"); axes[0].set_ylim(0.5, 1.0)
axes[0].legend(frameon=False, fontsize=7.8, loc="lower right")
fig.text(0.5, -0.10, "Solid: PPI++; dotted: real only. 1,000 random subsets per point.", ha="center", fontsize=8)
save(fig, "coverage.png")

# 4. integration levels and what this work covers
from matplotlib.patches import FancyBboxPatch
lv = [("L1 Sensor", "simulated camera, lidar and radar vs recorded sensor data", "not covered"),
      ("L2 Perception", "perception outputs on simulated vs real sensor input", "not covered"),
      ("L3 Other road users", "simulated vs recorded trajectories, close calls, collisions", "measured in av-sim-credibility"),
      ("L4 Planning in closed loop", "the automated vehicle's own decisions in re-simulated scenes", "not covered (recording vehicle replays its log)"),
      ("L5 System estimate", "event rates combining simulated and real exposure", "estimators tested on L3 outcomes (this report)")]
fig, ax = plt.subplots(figsize=(9, 4.2)); ax.set_xlim(0, 10); ax.set_ylim(0, 5.4); ax.axis("off")
for k, (name, desc, status) in enumerate(lv):
    y = 0.2 + k * 1.05; on = "not" not in status
    ax.add_patch(FancyBboxPatch((0.2, y), 5.9, 0.8, boxstyle="round,pad=0.02", fc="#e8eef8" if on else "white", ec=BLUE if on else GREY, lw=1.2))
    ax.text(0.4, y + 0.52, name, fontsize=10, weight="bold"); ax.text(0.4, y + 0.2, desc, fontsize=8.5, color="#333")
    ax.text(6.4, y + 0.38, status, fontsize=8.5, color=BLUE if on else GREY, va="center")
    if k < 4: ax.annotate("", (3.1, y + 1.03), (3.1, y + 0.82), arrowprops=dict(arrowstyle="->", color=GREY))
save(fig, "levels.png")
