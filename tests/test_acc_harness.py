# Changelog: 2026-10-03 | Antigravity (Claude Sonnet 5.5) | Tạo mới — test harness S2 (gradient, mask, khớp tham số, tái lập, rò rỉ split)
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from acc import harness as H  # noqa: E402
from acc.common import N_CAND  # noqa: E402
from acc.tasks import TASKS, make_split  # noqa: E402


def _small_batch(task="acc1", n=6):
    s = make_split(task, "train", n, 0)
    f, m, c = H.stack(s)
    z = H.P5Latent(f.shape[1]).fit(f)(f)
    return z, m, c


def test_loss_gradient_matches_finite_difference():
    rng = np.random.default_rng(0)
    logits = rng.standard_normal((3, N_CAND))
    mask = rng.random((3, N_CAND)) > 0.3
    correct = np.zeros_like(mask)
    correct[np.arange(3), [np.flatnonzero(mask[i])[0] for i in range(3)]] = True
    _, g = H._masked_softmax_loss(logits, mask, correct)
    for (i, j) in [(0, np.flatnonzero(mask[0])[1]), (2, np.flatnonzero(mask[2])[5])]:
        e = 1e-6
        lp, lm = logits.copy(), logits.copy()
        lp[i, j] += e
        lm[i, j] -= e
        num = (H._masked_softmax_loss(lp, mask, correct)[0] - H._masked_softmax_loss(lm, mask, correct)[0]) / (2 * e)
        assert num == pytest.approx(g[i, j], rel=1e-4, abs=1e-8)


def test_param_counts_matched_within_5pct():
    lin = H.LinearRank(64, 0)
    mlp = H.MLP(lin.n_params(), 0)
    assert abs(mlp.n_params() - lin.n_params()) / lin.n_params() < 0.05


def test_no_mask_violation_and_regret_zero_for_perfect_scores():
    s = make_split("acc1", "test", 20, 1)
    f, m, c = H.stack(s)
    scores = np.where(c, 1.0, 0.0)  # điểm hoàn hảo
    scores = np.where(m, scores, H.NEG)
    ev = H.evaluate(scores, m, c, s, "acc1")
    assert ev["top1"] == 1.0 and ev["mask_violations"] == 0 and ev["mean_regret"] == pytest.approx(0, abs=1e-9)


def test_masked_argmax_never_leaves_mask_even_with_adversarial_scores():
    s = make_split("acc1", "test", 20, 2)
    f, m, c = H.stack(s)
    adversarial = np.where(m, -1.0, 10.0)  # điểm cao nhất nằm ngoài mask
    sc = np.where(m, adversarial, H.NEG)
    assert H.evaluate(sc, m, c, s, "acc1")["mask_violations"] == 0


def test_training_reduces_loss_and_is_reproducible():
    z, m, c = _small_batch(n=24)
    losses = []
    for _ in range(2):
        mdl = H.MLP(50000, 3)
        log, _ = H.train_model(mdl, z, m, c, z, m, c, epochs=30, eval_every=10)
        losses.append([x[1] for x in log])
    assert losses[0] == losses[1]            # tái lập tuyệt đối
    assert losses[0][-1] < losses[0][0]      # loss giảm


@pytest.mark.parametrize("task", list(TASKS))
def test_splits_deterministic_and_disjoint_rng(task):
    a = make_split(task, "train", 5, 4)
    b = make_split(task, "train", 5, 4)
    t = make_split(task, "test", 5, 4)
    assert all(np.array_equal(x.features, y.features) for x, y in zip(a, b))
    assert not any(np.array_equal(x.features, y.features) for x, y in zip(a, t))
    for s in a + t:
        assert s.correct.any()
        assert (s.correct & s.infer_mask).any()  # luôn có đáp án trong mask suy luận


def test_acc2_acc3_infer_mask_does_not_leak_answer():
    for task in ("acc2", "acc3"):
        s = make_split(task, "test", 5, 0)
        assert all(x.infer_mask.all() for x in s)


def test_invalid_args_rejected():
    with pytest.raises(ValueError):
        make_split("acc1", "nope", 5, 0)
    with pytest.raises(ValueError):
        make_split("acc1", "train", 0, 0)


def test_bootstrap_ci_brackets_mean():
    lo, hi = H.bootstrap_ci(np.array([1, 0, 1, 1, 0, 1, 1, 1], float))
    assert lo <= 0.75 <= hi


def test_e9_rotor_gradients_match_finite_difference():
    z, m, c = _small_batch(n=4)
    mdl = H.E9CoreArm(True, 0)
    mdl.p["Wc"] *= 8  # tín hiệu đủ lớn để sai phân hữu hạn float32 ổn định
    logits, cache = mdl.forward(z)
    _, dlog = H._masked_softmax_loss(logits, m, c)
    g = mdl.grads(z, dlog.astype(np.float32), cache)

    def loss():
        return H._masked_softmax_loss(mdl.forward(z)[0], m, c)[0]

    for k in (0, 3, 6):
        e = 1e-2
        t0 = mdl.p["theta"][k]
        mdl.p["theta"][k] = t0 + e
        lp = loss()
        mdl.p["theta"][k] = t0 - e
        lm = loss()
        mdl.p["theta"][k] = t0
        assert (lp - lm) / (2 * e) == pytest.approx(float(g["theta"][k]), rel=5e-2, abs=2e-3)
    j = (5, 17)
    e = 1e-2
    w0 = mdl.p["Wc"][j]
    mdl.p["Wc"][j] = w0 + e
    lp = loss()
    mdl.p["Wc"][j] = w0 - e
    lm = loss()
    mdl.p["Wc"][j] = w0
    assert (lp - lm) / (2 * e) == pytest.approx(float(g["Wc"][j]), rel=5e-2, abs=2e-3)


def test_rotors_preserve_norm_and_zero_angle_equals_no_rotor():
    z, _, _ = _small_batch(n=5)
    h3, h4 = H.E9CoreArm(True, 1), H.E9CoreArm(False, 1)
    assert np.allclose(np.linalg.norm(h3._rot(z, h3.p["theta"]), axis=1), np.linalg.norm(z, axis=1), rtol=1e-4)
    h3.p["theta"][:] = 0
    assert np.allclose(h3.forward(z)[0], h4.forward(z)[0], atol=1e-5)
    assert h3.n_params() - h4.n_params() == 8
    assert abs(H.MLP(h3.n_params(), 0).n_params() - h3.n_params()) / h3.n_params() < 0.05


# ---------- H5/H6 (2026-10-04) ----------
def test_factor_incidence_matches_bruteforce_definition():
    G = H.factor_incidence(6, 4, (1, 2))
    assert G.shape == (24 + 15 * 16, N_CAND)
    assert np.all(G.sum(0) == 6 + 15)            # mỗi ứng viên chạm đúng 1 ô / factor
    from acc.common import decode
    k = 1234
    c = decode(k)                                 # qudit i = (k // 4**i) % 4
    on = set(np.flatnonzero(G[:, k]).tolist())
    assert {i * 4 + c[i] for i in range(6)} <= on  # unary ô đúng trạng thái
    Gq = H.factor_incidence(12, 2, (1,))
    assert all(Gq[j * 2 + ((k >> j) & 1), k] == 1 for j in range(12))


@pytest.mark.parametrize("name", list(H.FACTOR_SPECS))
def test_factor_arm_params_matched_and_gradient(name):
    m = H.FactorArm(name, 0)
    ref = H.E9CoreArm(True, 0).n_params()
    assert abs(m.n_params() - ref) / ref < 0.01, (m.n_params(), ref)
    z, mk, c = _small_batch(n=4)
    m.p["B"] *= 5  # ×20 làm logit bão hòa -> loss bị kẹp log(1e-30), sai phân hữu hạn mất nghĩa
    logits, cache = m.forward(z)
    _, dlog = H._masked_softmax_loss(logits, mk, c)
    g = m.grads(z, dlog.astype(np.float32), cache)
    for key, idx in (("B", (3, 7)), ("A", (11, 5)), ("c", (2,))):
        e = 1e-2
        w0 = m.p[key][idx]
        m.p[key][idx] = w0 + e
        lp = H._masked_softmax_loss(m.forward(z)[0], mk, c)[0]
        m.p[key][idx] = w0 - e
        lm = H._masked_softmax_loss(m.forward(z)[0], mk, c)[0]
        m.p[key][idx] = w0
        assert (lp - lm) / (2 * e) == pytest.approx(float(g[key][idx]), rel=5e-2, abs=2e-3)


def test_additive_arm_cannot_express_pairwise_coupling():
    """Δ_interaction có nghĩa: arm chỉ-unary không biểu diễn được hàm 'hai qudit bằng nhau'."""
    G = H.factor_incidence(6, 4, (1,))
    from acc.common import DIGITS
    target = (DIGITS[:, 0] == DIGITS[:, 1]).astype(float)
    coef, *_ = np.linalg.lstsq(G.T, target, rcond=None)
    assert np.abs(G.T @ coef - target).max() > 0.2
    G2 = H.factor_incidence(6, 4, (1, 2))
    coef2, *_ = np.linalg.lstsq(G2.T, target, rcond=None)
    assert np.abs(G2.T @ coef2 - target).max() < 1e-6
