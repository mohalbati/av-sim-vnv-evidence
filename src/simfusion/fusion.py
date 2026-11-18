"""Estimators that combine simulated and real results into one safety performance measure.

Setting (the standard one in sim-to-real fusion): a large set of N units has a cheap simulated outcome s_i; a small,
randomly chosen subset of n units also has the expensive real outcome y_i (paired: same scenario, real and simulated).
Target: theta = E[y], e.g. the real rate of conflicts (min TTC < tau) or collisions per vehicle.

  classical    mean of y on the n paired units                    (unbiased, ignores simulation)
  sim_only     mean of s on all N units                           (precise, biased by the sim-to-real gap)
  ppi          mean_N(s) + mean_n(y - s)                          (prediction-powered inference, Angelopoulos et al. 2023)
  ppi_pp       lambda * mean_N(s) + mean_n(y - lambda * s)        (PPI++ / control variate with tuned lambda, Angelopoulos et al. 2024)

Simulation supplies precision; the paired real units supply the bias correction. The variance reduction depends on the
per-unit correlation between y and s, so per-unit agreement matters even after the average bias is corrected.
Intervals are normal-approximation 95% intervals (z = 1.96). They under-cover for rare outcomes at small n (see the
technical report); use exact or betting-style (WSR) intervals there.
"""
import numpy as np

Z = 1.959964


def classical(y):
    y = np.asarray(y, float); n = y.size
    m = y.mean(); se = y.std(ddof=1) / np.sqrt(n)
    return {"est": m, "lo": m - Z * se, "hi": m + Z * se, "se": se}


def sim_only(s_all):
    s = np.asarray(s_all, float); m = s.mean(); se = s.std(ddof=1) / np.sqrt(s.size)
    return {"est": m, "lo": m - Z * se, "hi": m + Z * se, "se": se}


def ppi(y_lab, s_lab, s_unlab, lam=1.0):
    """PPI estimate with fixed lambda (lam = 1: classic PPI). s_unlab = simulated outcomes on units without a real label."""
    y, s, su = (np.asarray(a, float) for a in (y_lab, s_lab, s_unlab))
    n, N = y.size, su.size
    est = lam * su.mean() + (y - lam * s).mean()
    se = np.sqrt(lam ** 2 * su.var(ddof=1) / N + (y - lam * s).var(ddof=1) / n)
    return {"est": est, "lo": est - Z * se, "hi": est + Z * se, "se": se, "lam": lam}


def ppi_pp(y_lab, s_lab, s_unlab):
    """PPI++: lambda chosen to minimise variance, lambda* = cov(y, s) / ((1 + n/N) var(s)), clipped to [0, 1]."""
    y, s, su = (np.asarray(a, float) for a in (y_lab, s_lab, s_unlab))
    n, N = y.size, su.size
    vs = np.var(np.concatenate([s, su]), ddof=1)
    lam = 0.0 if vs == 0 else np.cov(y, s, ddof=1)[0, 1] / ((1 + n / N) * vs)
    return ppi(y, s, su, float(np.clip(lam, 0.0, 1.0)))


def effective_gain(se_classical, se_method):
    """How many times more real paired units the classical estimate would need to match the method's precision."""
    return (se_classical / se_method) ** 2


def hierarchical_log_ratio(log_r, se):
    """Empirical-Bayes normal-normal model for per-family log tail ratios (DerSimonian-Laird between-family variance).
    log R_f ~ N(mu, tau^2), observed with standard error se_f. Returns mu, tau and the partially pooled values."""
    log_r, se = np.asarray(log_r, float), np.asarray(se, float)
    w = 1 / se ** 2
    mu_fe = np.sum(w * log_r) / np.sum(w)
    q = np.sum(w * (log_r - mu_fe) ** 2); k = log_r.size
    tau2 = max(0.0, (q - (k - 1)) / (np.sum(w) - np.sum(w ** 2) / np.sum(w)))
    wr = 1 / (se ** 2 + tau2)
    mu = np.sum(wr * log_r) / np.sum(wr)
    shrink = tau2 / (tau2 + se ** 2)
    pooled = mu + shrink * (log_r - mu)
    post_se = np.sqrt(shrink * se ** 2 + (1 - shrink) ** 2 / np.sum(wr))
    return {"mu": mu, "tau": np.sqrt(tau2), "pooled": pooled, "pooled_se": post_se, "shrink": shrink}


def theoretical_gain(rho, n=500, N=None):
    """Large-sample gain of the tuned estimator over real-only: 1 / (1 - rho^2 / (1 + n/N)); N=None means N >> n."""
    f = 1.0 if N is None else 1.0 + n / N
    return 1.0 / (1.0 - rho ** 2 / f)


def rho_max_binary(p_real, p_sim):
    """Largest possible correlation between two 0/1 outcomes with these rates (reached when the events nest)."""
    lo, hi = min(p_real, p_sim), max(p_real, p_sim)
    return float(np.sqrt(lo * (1 - hi) / (hi * (1 - lo))))
