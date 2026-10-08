import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from trialforecast import scoring as s


def test_brier_constant_base_rate():
    # A constant forecast equal to the event rate scores rate * (1 - rate).
    y = np.array([1] * 43 + [0] * 57)
    assert s.brier(np.full(100, 0.43), y) == pytest.approx(0.43 * 0.57)


def test_brier_perfect_and_worst():
    y = np.array([1, 0, 1, 0])
    assert s.brier(y, y) == 0
    assert s.brier(1 - y, y) == 1


def test_log_score_clips_extremes():
    y = np.array([1, 0])
    assert s.log_score([0.0, 1.0], y) == pytest.approx(-np.log(0.01))
    assert s.log_score([0.5, 0.5], y) == pytest.approx(np.log(2))


def test_brier_skill_sign():
    y = np.array([1, 1, 0, 0])
    ref = np.full(4, 0.5)
    assert s.brier_skill([0.9, 0.8, 0.2, 0.1], y, ref) > 0
    assert s.brier_skill([0.1, 0.2, 0.8, 0.9], y, ref) < 0
    assert s.brier_skill(ref, y, ref) == pytest.approx(0)


def test_murphy_identity_exact_for_discrete_forecasts():
    rng = np.random.default_rng(1)
    p = rng.choice([0.05, 0.25, 0.45, 0.65, 0.85], size=2000)
    y = (rng.random(2000) < p).astype(float)
    d = s.murphy_decomposition(p, y, bins=10)
    assert d["reliability"] - d["resolution"] + d["uncertainty"] == pytest.approx(s.brier(p, y), abs=1e-12)


def test_auc_known_values():
    assert s.auc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 1.0
    assert s.auc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0.0
    assert s.auc([0.5, 0.5, 0.5, 0.5], [1, 1, 0, 0]) == 0.5


def test_crps_normal_matches_numerical_integral():
    mu, sigma, x = -0.3, 0.2, -0.1
    num, _ = quad(lambda t: (norm.cdf(t, mu, sigma) - (t >= x)) ** 2, mu - 10 * sigma, mu + 10 * sigma, points=[x])
    assert float(s.crps_normal(mu, sigma, x)) == pytest.approx(num, rel=1e-6)


def test_crps_point_forecast_is_absolute_error():
    out = s.crps_normal([0.0, -0.3], [0.0, 0.0], [0.2, -0.1])
    assert out == pytest.approx([0.2, 0.2])


def test_crps_mixed_point_and_distribution():
    out = s.crps_normal([0.0, 0.0], [0.0, 1.0], [0.5, 0.5])
    assert out[0] == pytest.approx(0.5)
    assert out[1] == pytest.approx(float(s.crps_normal(0.0, 1.0, 0.5)))


def test_interval_score_penalises_misses():
    assert float(s.interval_score(-0.5, -0.1, -0.3, alpha=0.2)) == pytest.approx(0.4)
    assert float(s.interval_score(-0.5, -0.1, 0.0, alpha=0.2)) == pytest.approx(0.4 + 10 * 0.1)


def test_log_score_normal_matches_scipy():
    assert float(s.log_score_normal(0.0, 1.0, 0.0)) == pytest.approx(0.5 * np.log(2 * np.pi))


def test_cluster_bootstrap_detects_real_difference_and_widens_with_clustering():
    rng = np.random.default_rng(0)
    n = 300
    a = rng.normal(0.20, 0.05, n)
    b = a + rng.normal(0.03, 0.05, n)  # b is worse by 0.03 on average
    indep = s.paired_cluster_bootstrap(a, b, np.arange(n), n_boot=2000)
    assert indep["mean_diff"] == pytest.approx(float((a - b).mean()))
    assert indep["ci_high"] < 0 and indep["p_two_sided"] < 0.05
    # Same differences, but perfectly shared within 10 clusters: the interval must be wider.
    shared = np.repeat(rng.normal(-0.03, 0.05, 10), 30)
    clustered = s.paired_cluster_bootstrap(shared, np.zeros(n), np.repeat(np.arange(10), 30), n_boot=2000)
    unclustered = s.paired_cluster_bootstrap(shared, np.zeros(n), np.arange(n), n_boot=2000)
    assert (clustered["ci_high"] - clustered["ci_low"]) > (unclustered["ci_high"] - unclustered["ci_low"])
    assert clustered["n_clusters"] == 10


def test_cluster_bootstrap_null_is_not_significant():
    rng = np.random.default_rng(3)
    a = rng.normal(0.2, 0.05, 200)
    b = a + rng.normal(0.0, 0.05, 200)
    out = s.paired_cluster_bootstrap(a, b, np.arange(200), n_boot=2000)
    assert out["ci_low"] < 0 < out["ci_high"]


def test_a_bootstrap_p_value_is_never_reported_as_zero():
    # Every resample favours a: the p-value can only be said to be below what the resamples can resolve.
    result = s.paired_cluster_bootstrap([0.0] * 20, [1.0] * 20, list(range(20)), n_boot=999)
    assert result["p_two_sided"] == pytest.approx(2 / 1000)
