"""Proper scoring rules and paired comparisons for trial forecasts.

Binary target: did the trial meet its primary endpoint (1) or not (0).
Continuous target: the log hazard ratio of the primary endpoint.
Lower is better for every score in this module.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


# --- binary forecasts -------------------------------------------------------

def brier(p, y) -> float:
    p, y = _arr(p), _arr(y)
    return float(np.mean((p - y) ** 2))


def log_score(p, y, clip: tuple[float, float] = (0.01, 0.99)) -> float:
    """Mean negative log likelihood, with forecasts clipped to a pre-registered range."""
    p, y = np.clip(_arr(p), *clip), _arr(y)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier_skill(p, y, p_ref) -> float:
    """1 - BS/BS_ref. Positive means better than the reference forecast."""
    return 1.0 - brier(p, y) / brier(p_ref, y)


def murphy_decomposition(p, y, bins: int = 10) -> dict[str, float]:
    """Reliability, resolution and uncertainty over equal-width probability bins.

    brier = reliability - resolution + uncertainty holds exactly when every
    forecast in a bin is identical; otherwise the within-bin term is the gap.
    """
    p, y = _arr(p), _arr(y)
    base = y.mean()
    idx = np.minimum((p * bins).astype(int), bins - 1)
    rel = res = 0.0
    for b in np.unique(idx):
        m = idx == b
        w = m.mean()
        rel += w * (p[m].mean() - y[m].mean()) ** 2
        res += w * (y[m].mean() - base) ** 2
    return {"reliability": float(rel), "resolution": float(res), "uncertainty": float(base * (1 - base))}


def auc(p, y) -> float:
    """Probability a random positive is ranked above a random negative (ties count half)."""
    p, y = _arr(p), _arr(y)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    diff = pos[:, None] - neg[None, :]
    return float(((diff > 0).sum() + 0.5 * (diff == 0).sum()) / diff.size)


def wilson_interval(positive: int, trials: int, level: float = 0.95) -> tuple[float | None, float | None]:
    """The Wilson score interval for a share: it stays inside 0 and 1 and behaves with few trials."""
    if trials == 0:
        return None, None
    z = norm.ppf(0.5 + level / 2)
    share, spread = positive / trials, z * z / trials
    centre = (share + spread / 2) / (1 + spread)
    half = z * np.sqrt(share * (1 - share) / trials + spread / (4 * trials)) / (1 + spread)
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


# --- continuous forecasts of the log hazard ratio ---------------------------

def crps_normal(mu, sigma, x) -> np.ndarray:
    """CRPS of a normal predictive distribution; reduces to |mu - x| when sigma is 0."""
    mu, sigma, x = _arr(mu), _arr(sigma), _arr(x)
    out = np.abs(mu - x)
    pos = sigma > 0
    if np.any(pos):
        z = (x - mu)[pos] / sigma[pos] if out.ndim else (x - mu) / sigma
        s = sigma[pos] if out.ndim else sigma
        val = s * (z * (2 * norm.cdf(z) - 1) + 2 * norm.pdf(z) - 1 / np.sqrt(np.pi))
        if out.ndim:
            out[pos] = val
        else:
            out = val
    return out


def interval_score(lower, upper, x, alpha: float = 0.2) -> np.ndarray:
    """Interval score for a central (1 - alpha) prediction interval."""
    lower, upper, x = _arr(lower), _arr(upper), _arr(x)
    return (upper - lower) + (2 / alpha) * np.maximum(lower - x, 0) + (2 / alpha) * np.maximum(x - upper, 0)


def log_score_normal(mu, sigma, x) -> np.ndarray:
    return -norm.logpdf(_arr(x), loc=_arr(mu), scale=_arr(sigma))


# --- paired comparison with clustering --------------------------------------

def paired_cluster_bootstrap(score_a, score_b, clusters, n_boot: int = 10_000, seed: int = 0) -> dict[str, float]:
    """Mean per-trial score difference (a - b) with a cluster bootstrap over, e.g., drug.

    Whole clusters are resampled so that trials of the same drug move together.
    Negative mean_diff means forecaster a scored better (lower) than b.
    """
    d = _arr(score_a) - _arr(score_b)
    clusters = np.asarray(clusters)
    ids, inv = np.unique(clusters, return_inverse=True)
    sums = np.bincount(inv, weights=d, minlength=len(ids))
    counts = np.bincount(inv, minlength=len(ids))
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(ids), size=(n_boot, len(ids)))
    boot = sums[pick].sum(axis=1) / counts[pick].sum(axis=1)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    # One is added to each count so that a p-value is never reported as zero: resampling
    # cannot show a probability smaller than one in the number of resamples.
    p_two = 2 * min((boot <= 0).sum() + 1, (boot >= 0).sum() + 1) / (n_boot + 1)
    return {
        "mean_diff": float(d.mean()),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "p_two_sided": float(min(1.0, p_two)),
        "n_trials": int(len(d)),
        "n_clusters": int(len(ids)),
    }
