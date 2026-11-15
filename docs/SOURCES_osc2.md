# Card pipeline batch 2 (`engine15/sources/osc2.py`)

The owner gave the go on 15 Nov 2026 (see `research/CARD_PIPELINE.md`). Five cards, built only from the asset's own
15-minute bars, on all eight markets. They are **reading-only**: they are not in `sources.MODULES` yet and do not
vote. **Nothing here is claimed to predict anything.** Tests: `tests/test_sources_osc2.py`.

## The timing rule

A row is keyed by its 15m bar's OPEN time and uses only what was known at that bar's close. 1h, 4h and daily values
are computed on resampled OHLCV bars (UTC grid, left-labelled) and reach a 15m row only once that higher bar has
closed (`data.htf_on_15`). The tests cut the history at several points and check that no column changes, and that
daily / 4h values change only on the row whose close is the higher bar's close. `update()` fetches nothing.

## The cards

| Voice | Card | What it reads | Parameters |
|---|---|---|---|
| `psar` | Parabolic SAR (15m to daily) | Wilder's SAR direction on 15m, 1h, 4h, 1d (+1 up / -1 down) and how many agree (`psar_agree` = sum / 4). Raw: SAR level as charts draw it for the bar (`psar_lvl_*`), close minus SAR in ATR(14) of that timeframe (`psar_dist_*`), bars since the last flip (`psar_since_*`) | step 0.02, max 0.2, seeded on the first two bars |
| `mfi` | Money Flow Index (15m to daily) | MFI on each timeframe, feature (MFI - 50) / 50; raw `mfi_raw_*`; the sentence flags >= 80 overbought, <= 20 oversold | MFI(14), typical price x volume |
| `vprofile` | Volume profile (session and 7 days) | Volume at price over (a) the UTC day so far, up to and including the row's bar, and (b) the trailing 7 x 24 hours. Point of control (POC) and the 70% value area (VAL-VAH). `vpf_pos_*`: -1 below VAL, +1 above VAH, -0.5..+0.5 inside by where in the area; `vpf_poc_*`: (close - POC) / daily ATR / 2, clipped. Raw: `vpf_poc_px_*`, `vpf_vah_px_*`, `vpf_val_px_*`, `vpf_poc_atr_*` | each bar's volume sits at its typical price; bins of 0.1 x ATR(14) of the last closed daily bar (widened if the window needs more than 200 bins); value area grown from the POC one bin at a time toward the heavier neighbour; needs 4 bars (day) / 96 bars (7 days) |
| `heikin` | Heikin-Ashi trend (15m to 4h) | HA candle colour (+1 green / -1 red; equal counts red), current colour run as sign x min(run, 10) / 10, strong candle (+1 green with no lower wick, -1 red with no upper wick, else 0). Raw: `ha_runlen_*` | HA open seeded at (open + close) / 2 of the first bar |
| `aroon` | Aroon and Vortex (1h to daily) | Aroon up / down scaled (x - 50) / 50, Aroon oscillator (up - down) / 100, Vortex (VI+ - VI-) / 0.5 clipped, on 1h, 4h, 1d. Raw: `aro_up_raw_*`, `aro_dn_raw_*`, `vtx_plus_*`, `vtx_minus_*` | Aroon(25) over the last 26 bars (ties: most recent extreme); Vortex(14) |

Features are in [-1, 1] with 0.0 = no read (never NaN); raw columns are NaN when there is no read. `describe(row,
asset)` gives one sentence per card that says what is read and forecasts nothing.

## Volume

- **USDJPY: no read** for MFI and the volume profile on every row (`NO_VOLUME`); its live feed carries no volume
  (always 0 since the Yahoo join, `docs/EXTDATA.md`). The sentence says so.
- Any asset: a window is read only if at least half its bars carry volume > 0 (a bars frame without a volume column
  reads nothing on these two cards).
- Gold, silver, the S&P, WTI and Brent do carry volume, but it is each source's own number (Dukascopy quoted size, or
  tick-like volume) and gold, silver and the S&P change source at the data join (Aug / Sep 2026). Read their MFI and
  profiles with that in mind; volume is not comparable across markets.

## Cost

BTCUSDT full history (about 276,000 15m rows, 2019 to Nov 2026): about 6 s for all five cards on the owner's laptop.
