# -*- coding: utf-8 -*-
"""osc2 (card pipeline batch 2: Parabolic SAR, MFI, volume profile, Heikin-Ashi, Aroon/Vortex): no look-ahead,
sane ranges, higher timeframes wait for their close, plain-English cards, honest "no read" without volume."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine15 import sources  # noqa: E402
from engine15.sources import osc2  # noqa: E402


def bars(n=96 * 60, seed=5, volume=True):
    rng = np.random.RandomState(seed)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.concatenate([[100.0], c[:-1]])
    sp = np.abs(rng.normal(0, 0.002, n)) * c
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": o, "high": np.maximum(o, c) + sp, "low": np.minimum(o, c) - sp, "close": c}, index=idx)
    if volume:
        df["volume"] = rng.lognormal(3.0, 0.6, n)
    return df


B = bars()
FULL = osc2.features(B.index, "TEST", bars=B)


def test_no_look_ahead():
    for cut in (96 * 20 + 7, 96 * 33 + 50, 96 * 47 + 16, len(B) - 3):
        part = osc2.features(B.index[:cut], "TEST", bars=B.iloc[:cut])
        a = FULL.iloc[:cut][osc2.FEATURES + osc2.RAW].values.astype(float)
        p = part[osc2.FEATURES + osc2.RAW].values.astype(float)
        bad = ~np.isclose(a, p, equal_nan=True, atol=1e-9)
        assert not bad.any(), (cut, [c for c, x in zip(osc2.FEATURES + osc2.RAW, bad.any(axis=0)) if x])


def test_ranges_and_reads():
    f = FULL
    assert not f.attrs["errors"], f.attrs["errors"]
    assert not f[osc2.FEATURES].isna().any().any()
    assert (f[osc2.FEATURES].abs() <= 1.0).all().all()
    late = f.iloc[-1]
    for tag, _ in osc2.TFS4:
        assert late["psar_" + tag] in (-1.0, 1.0)
        assert 0.0 <= late["mfi_raw_" + tag] <= 100.0
        d = late["psar_dist_" + tag]
        assert (d > 0) == (late["psar_" + tag] > 0)                     # SAR under price when up, over it when down
    for tag, _ in osc2.TFS_HA:
        assert late["ha_col_" + tag] in (-1.0, 1.0) and late["ha_runlen_" + tag] >= 1
        assert late["ha_strong_" + tag] in (-1.0, 0.0, 1.0)
    for tag, _ in osc2.TFS_AR:
        assert 0.0 <= late["aro_up_raw_" + tag] <= 100.0 and 0.0 <= late["aro_dn_raw_" + tag] <= 100.0
        assert late["vtx_plus_" + tag] > 0 and late["vtx_minus_" + tag] > 0
    for w in ("day", "7d"):
        assert late["vpf_val_px_" + w] <= late["vpf_poc_px_" + w] <= late["vpf_vah_px_" + w]
    assert f["vpf_poc_px_7d"].iloc[96 * 16:].notna().all()                # after the daily ATR(14) exists


def test_value_area_holds_seventy_percent():
    """Recompute one 7-day profile by hand: the value area holds >= 70% of the window's volume and contains the POC."""
    i = len(B) - 1
    t = B.index[i]
    win = B[B.index > t - pd.Timedelta(days=7)]
    tp = (win["high"] + win["low"] + win["close"]) / 3.0
    row = FULL.iloc[i]
    inside = (tp >= row["vpf_val_px_7d"] - 1e-9) & (tp < row["vpf_vah_px_7d"] + 1e-9)
    assert win["volume"][inside].sum() >= 0.7 * win["volume"].sum() - 1e-6


def test_higher_timeframes_wait_for_their_close():
    close = FULL.index + pd.Timedelta(minutes=15)                       # rows keyed by OPEN time: the CLOSE decides
    day, h4 = close.normalize(), close.floor("4h")
    for col in ("mfi_raw_1d", "psar_lvl_1d", "aro_up_raw_1d", "vtx_plus_1d"):
        s = FULL[col]
        for d in day.unique()[-5:]:
            assert s[day == d].dropna().nunique() <= 1, (col, d)
    for col in ("ha_runlen_4h", "mfi_raw_4h", "psar_lvl_4h", "aro_dn_raw_4h"):
        s = FULL[col]
        for g in h4.unique()[-12:]:
            assert s[h4 == g].dropna().nunique() <= 1, (col, g)
    # a daily value changes only on the row whose close is midnight UTC
    s = FULL["mfi_raw_1d"].dropna()
    changed = s.index[1:][s.values[1:] != s.values[:-1]]
    assert len(changed) and ((changed + pd.Timedelta(minutes=15)) == (changed + pd.Timedelta(minutes=15)).normalize()).all()


def test_describe_one_sentence_per_card():
    say = osc2.describe(FULL.iloc[-1], "TEST")
    assert list(say) == [t for t, _ in osc2.GROUPS.values()]
    for title, text in say.items():
        assert isinstance(text, str) and text.endswith(".") and text.count(". ") == 0, (title, text)
    assert "Parabolic SAR" in say["Parabolic SAR (15m to daily)"]
    assert "POC" in say["Volume profile (session and 7 days)"]
    assert "no read" not in say["Money Flow Index (15m to daily)"]


def test_no_volume_is_no_read():
    nb = bars(n=96 * 20, volume=False)
    for asset, b in (("TEST", nb), ("USDJPY", bars(n=96 * 20))):        # no volume column; or a no-volume market
        f = osc2.features(b.index, asset, bars=b)
        vcols = [c for c in osc2.FEATURES + osc2.RAW if c.startswith(("mfi", "vpf"))]
        assert f[[c for c in vcols if c in osc2.RAW]].isna().all().all()
        assert (f[[c for c in vcols if c in osc2.FEATURES]] == 0.0).all().all()
        assert f["psar_lvl_15m"].notna().any()                         # the other cards still read
        say = osc2.describe(f.iloc[-1], asset)
        assert "no read" in say["Money Flow Index (15m to daily)"]
        assert "no read" in say["Volume profile (session and 7 days)"]
    assert "USDJPY" in say["Money Flow Index (15m to daily)"]
    zero = bars(n=96 * 20)
    zero["volume"] = 0.0
    f = osc2.features(zero.index, "TEST", bars=zero)
    assert f["mfi_raw_15m"].isna().all() and f["vpf_poc_px_7d"].isna().all()


def test_psar_textbook():
    """A steady climb stays UP with the SAR under the lows; a sharp drop flips it DOWN at the prior extreme."""
    n = 60
    idx = pd.date_range("2025-01-01", periods=n, freq="15min", tz="UTC")
    c = np.r_[np.linspace(100, 130, 40), np.linspace(125, 100, 20)]
    df = pd.DataFrame({"open": c, "high": c + 0.5, "low": c - 0.5, "close": c}, index=idx)
    sar, dr, since = osc2.psar(df)
    assert (dr[1:40] == 1).all() and (sar[2:40] < df["low"].values[2:40]).all()
    j = int(np.argmax(dr[40:] < 0)) + 40
    assert dr[j] == -1 and since[j] == 0 and abs(sar[j] - df["high"].values[:j].max()) < 1e-9


def test_not_wired_in_yet():
    assert "osc2" not in sources.MODULES                                 # the parent session wires it as v5.1.2


def test_index_unit_does_not_matter():
    """data.load gives a millisecond index; pandas arithmetic can return microseconds. Same readings either way."""
    bm = B.copy()
    bm.index = bm.index.as_unit("ms")
    f = osc2.features(bm.index, "TEST", bars=bm)
    assert f["vpf_poc_px_7d"].notna().sum() == FULL["vpf_poc_px_7d"].notna().sum() > 0
    assert np.allclose(f[osc2.FEATURES + osc2.RAW].values, FULL[osc2.FEATURES + osc2.RAW].values, equal_nan=True)
