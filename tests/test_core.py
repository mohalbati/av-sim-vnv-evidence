"""Tests against known answers. Run: python tests/test_core.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from simfusion import fusion, levels


def test_fusion_ppi():
    r = np.random.default_rng(3); N, n = 20000, 400
    z = r.standard_normal((N, 2)); zs = 0.9 * z[:, 0] + np.sqrt(1 - 0.81) * z[:, 1]
    y = (z[:, 0] < -1.6).astype(float); s = (zs < -1.2).astype(float)        # biased but correlated simulator
    errs_c, errs_p, cov = [], [], 0
    for _ in range(300):
        idx = r.permutation(N); lab, unl = idx[:n], idx[n:]
        c = fusion.classical(y[lab]); p = fusion.ppi_pp(y[lab], s[lab], s[unl])
        errs_c.append(c["est"] - y.mean()); errs_p.append(p["est"] - y.mean()); cov += p["lo"] <= y.mean() <= p["hi"]
    assert abs(np.mean(errs_p)) < 0.003                                       # bias corrected
    assert np.std(errs_p) < np.std(errs_c)                                    # simulation adds precision
    assert cov / 300 > 0.90
    assert abs(fusion.sim_only(s)["est"] - y.mean()) > 0.03                   # sim alone is biased
    lam = fusion.ppi_pp(y[:300], r.random(300), r.random(5000))["lam"]
    assert lam < 0.3                                                          # unrelated simulator gets ~no weight


def test_hierarchical_shrinkage():
    h = fusion.hierarchical_log_ratio([0.0, 0.0, 0.0, 2.0], [0.1, 0.1, 0.1, 0.5])
    assert h["pooled"][3] < 2.0 and h["shrink"][3] < h["shrink"][0]          # the noisy outlier is pulled in more


def test_levels_table():
    assert len(levels.LEVELS) == 5
    assert all(l["level"] in levels.STATUS for l in levels.LEVELS)


def test_gain_formula():
    # gain 1 / (1 - rho^2 / (1 + n/N)) from the variance of the tuned estimator
    assert np.isclose(fusion.theoretical_gain(0.0), 1.0)
    assert abs(fusion.theoretical_gain(np.sqrt(0.5), n=500, N=1e9) - 2.0) < 1e-6


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t(); print("PASS", t.__name__)
    print(f"{len(tests)} tests passed")
