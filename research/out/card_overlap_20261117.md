# Duplicate cards (H54): which cards say the same thing, and does one idea vote several times?

Tag 20261117. Engine think15-v5.2.4. DESCRIPTIVE, in-sample history before the sealed holdout (2025-11-11); halves split at 2023-06-07. Registered in research/HYPOTHESES.md (H54) before this code existed. **Nothing here removes, merges or re-weights a card: that is a new engine version and the owner's decision.** A high overlap says two cards lean together; it does not say either of them is right, and it proves no edge.

## Plain-English summary (for the owner)

**The question.** The engine reads 82 cards. Do some of them say the same thing, and does one idea get several votes?

**Two ways of being "the same".** Two cards can READ the same thing (their numbers move together) and still VOTE
differently, because each card learns its own way of turning its readings into a lean. The registered definition of a
duplicate is about the vote (the card's pull on the odds); the readings are reported beside it. Both matter: the vote
tells you whether an idea is counted twice today, the readings tell you which cards are the same raw material.

**What was found** (history before November 2025, both halves, four market groups; the S&P group was not run because
its reading cache was one version behind):

1. **No two cards are duplicates by their vote.** No pair reaches the 0.85 bar in any group. The closest anywhere is
   about 0.80 (CCI with Williams %R in crypto and USDJPY).
2. **Two pairs are near-duplicates by their vote:**
   - **"Stretch and exhaustion" and the new "StochRSI" card, in all four groups** (0.66 to 0.85). No surprise: the
     Stretch card already reads StochRSI on 15m, 1h and 4h itself; the StochRSI card's readings are matched 0.91 by it.
   - **"Momentum" and "Order flow (CVD)" in crypto** (0.73 / 0.75). Both are current crypto voters, so in crypto this
     one idea ("which way have price and buying been going") votes twice; together they hold about 15% of the say.
     It is the only case in any group where two current voters vote alike.
3. **By what they READ, there is one large family of near-copies and a few small ones:**
   - **CCI and Williams %R are the same reading** (0.87 to 0.90 in every group). Neither votes anywhere today.
   - **A family of seven that all answer "where is price inside its recent range / against its averages":** Stretch
     and exhaustion, Moving-average ribbon, KAMA, StochRSI, CCI, Williams %R, Elder-Ray. Each one's readings are matched
     0.70 to 0.88 by another's.
   - **Timeframe strength and Moving averages** (0.83 to 0.84): the trend score is built from the same moving averages.
   - **Intraday levels (VWAP) and Volume profile** (about 0.8, where volume exists).
4. **What is NOT duplicated, although it sounds as if it should be:** the trend followers Supertrend, Parabolic SAR and
   Heikin-Ashi overlap only 0.4 to 0.5 with each other on both measures; Chaikin money flow and Money Flow Index 0.45;
   Fisher, TRIX, Ultimate Oscillator, the regression channel, Mass Index, Aroon/Vortex, RSI divergence, the range
   budget, Hull and every crypto positioning card do not reach 0.70 with any other card across the groups, on either
   measure.

**Is one idea over-represented among the voters?**

| Group | By the vote | By the readings |
|---|---|---|
| Crypto (12 voters) | Momentum + Order flow: 2 voters, about 15% of the say | no family holds two voters |
| Gold and silver (13) | none | the range/average family holds 3 voters (Momentum, Stretch, KAMA: about 23% of the say) and the trend family 2 (Timeframe strength, Moving averages: about 15%); together 5 of 13 voters and about 38% of the say |
| USDJPY (12) | none | Timeframe strength + Moving averages (about 17%) and Momentum + Stretch (about 18%): 4 of 12 voters, about 35% |
| Oil (10) | none | none |

So the voters are less repetitive than the card list suggests: by how they actually vote, each group's voters are
all separate ideas except one pair (crypto: 11 ideas from 12 voters; gold/silver 13, USDJPY 12, oil 10). The repetition is mostly among cards that do NOT vote (the new oscillator
batches), and in gold/silver and USDJPY among voters that read the same raw material but lean differently.

**What a clean-up could look like: options, not recommendations.** Nothing changes unless the owner says so; any of
these is a new engine version and would be registered first.

- **A. Leave everything.** Reading-only cards cost nothing in the vote. The price is a longer card list on the page and
  in the journal.
- **B. Tidy the page only.** Group the near-copies under one heading (for example "Range position: Stretch, StochRSI,
  CCI, Williams %R, Elder-Ray") so one idea is seen once. No change to readings or votes.
- **C. Retire the plainest copies from the card list.** The clearest candidates by this study: Williams %R (the same
  reading as CCI, and rated below it in three of four groups) and the separate StochRSI card (already inside Stretch and
  exhaustion). Both are reading-only, so no vote changes; it still changes what is journaled.
- **D. A promotion rule for the pipeline.** When a new card is proposed for a vote (step 5), also check that it is not
  a near-copy of a card that already votes in that group. This matters soon: CCI, Elder-Ray, the ribbon and KAMA rate
  well in several groups and are all in the same family, so promoting two of them together would give one idea two
  votes.
- **E. Look at crypto's Momentum + Order flow pair** at the next voting review: keep both (15% for one idea is far under
  the 40% cap), or let only the better-rated of the two vote. In the 17 Nov rating Momentum and stretch is #4 and Order
  flow #21 in crypto.

**How sure is this?** It describes how the cards behaved together on history that has been looked at before. The
thresholds (0.85 and 0.70) were fixed before looking and are conventions. Pairs just under a line (CCI with Williams %R
by vote: 0.69 across groups) are not meaningfully different from pairs just over it. A card that copies another on
history can still differ on the rare days that matter. None of this says any card is right, and no card has a proven
edge.

## How it was measured

- Groups: crypto (BTCUSDT, ETHUSDT; 240306 rows, sessions 2020-01-01 00:00 .. 2025-11-10 23:45), metals (XAUUSD, XAGUSD; 162215 rows, sessions 2020-01-01 23:00 .. 2025-11-10 23:45), fx (USDJPY; 171130 rows, sessions 2020-01-01 22:00 .. 2025-11-10 23:45), energy (WTI, BRENT; 147360 rows, sessions 2020-01-02 01:00 .. 2025-11-10 21:45). Not run: index.
- A voice's **pull** = P(up) - P(down) of its own odds, formed as the engine forms them (weekly refits walked forward from 2020). **Pull overlap** = Spearman rank correlation of two voices' pulls on the sessions where both speak (at least 2000 a half and asset); **agreement** = how often the two pulls have the same sign there; **reading overlap** = how closely each reading of one card is matched by some reading of the other (mean of the best |rank correlation|, the weaker direction).
- In a group a pair's similarity is the weaker half's |pull overlap| (0 if its sign flips). Across groups: the value reached in at least three quarters of the groups where both cards are measured. **Duplicate: >= 0.85. Near-duplicate: >= 0.70.** Clusters: average linkage at those thresholds.
- Pairs measured: 2251 (across 71 voices). No significance test is run; the thresholds are conventions fixed before looking.

## 1. Pairs that vote alike (pull overlap at or above 0.70 across groups)

Per group: pull overlap 1st half / 2nd half (agreement % in the weaker half), then reading overlap of the weaker half.

| card A | card B | S | label | groups | crypto | metals | fx | energy | readings |
|---|---|---|---|---|---|---|---|---|---|
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | StochRSI (15m to daily) (`stochrsi`) | 0.75 | near-duplicate | 4 | 0.66 / 0.74 (73%), r 0.78 | 0.75 / 0.78 (78%), r 0.80 | 0.80 / 0.85 (81%), r 0.80 | 0.81 / 0.78 (80%), r 0.80 | 0.80 reads nearly alike |
| Momentum and stretch: Momentum (`momentum`) | Order flow (CVD) (`flow`) | 0.73 | near-duplicate | 1 | 0.73 / 0.75 (76%), r 0.49 | - | - | - | 0.49 |

## 2. Pairs that READ alike (reading overlap at or above 0.70) but whose votes overlap less than 0.70

| card A | card B | reading overlap | label | pull overlap S |
|---|---|---|---|---|
| CCI (15m to daily) (`cci`) | Williams %R (15m to daily) (`willr`) | 0.88 | reads alike | 0.69 |
| Timeframe strength (`trend`) | Moving averages (SMA and EMA 5-200) (`mavg`) | 0.83 | reads nearly alike | 0.52 |
| Moving-average ribbon (`ribbon`) | Kaufman adaptive average (KAMA) (`kama`) | 0.83 | reads nearly alike | 0.45 |
| CCI (15m to daily) (`cci`) | Elder-Ray (1h to daily) (`elder`) | 0.81 | reads nearly alike | 0.57 |
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | Moving-average ribbon (`ribbon`) | 0.81 | reads nearly alike | 0.46 |
| Moving-average ribbon (`ribbon`) | Williams %R (15m to daily) (`willr`) | 0.80 | reads nearly alike | 0.42 |
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | Williams %R (15m to daily) (`willr`) | 0.80 | reads nearly alike | 0.59 |
| Intraday levels (VWAP and opening range) (`intraday`) | Volume profile (session and 7 days) (`vprofile`) | 0.79 | reads nearly alike | 0.41 |
| Moving-average ribbon (`ribbon`) | CCI (15m to daily) (`cci`) | 0.79 | reads nearly alike | 0.52 |
| Kaufman adaptive average (KAMA) (`kama`) | Williams %R (15m to daily) (`willr`) | 0.78 | reads nearly alike | 0.23 |
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | CCI (15m to daily) (`cci`) | 0.77 | reads nearly alike | 0.50 |
| Momentum and stretch: Momentum (`momentum`) | CCI (15m to daily) (`cci`) | 0.77 | reads nearly alike | 0.55 |
| StochRSI (15m to daily) (`stochrsi`) | Williams %R (15m to daily) (`willr`) | 0.76 | reads nearly alike | 0.68 |
| Kaufman adaptive average (KAMA) (`kama`) | CCI (15m to daily) (`cci`) | 0.76 | reads nearly alike | 0.35 |
| Moving-average ribbon (`ribbon`) | Elder-Ray (1h to daily) (`elder`) | 0.75 | reads nearly alike | 0.37 |
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | Kaufman adaptive average (KAMA) (`kama`) | 0.75 | reads nearly alike | 0.37 |
| Moving averages (SMA and EMA 5-200) (`mavg`) | Elder-Ray (1h to daily) (`elder`) | 0.75 | reads nearly alike | 0.39 |
| Moving averages (SMA and EMA 5-200) (`mavg`) | CCI (15m to daily) (`cci`) | 0.74 | reads nearly alike | 0.37 |
| Momentum and stretch: Momentum (`momentum`) | Momentum and stretch: Stretch and exhaustion (`meanrev`) | 0.74 | reads nearly alike | 0.29 |
| Momentum and stretch: Momentum (`momentum`) | Williams %R (15m to daily) (`willr`) | 0.74 | reads nearly alike | 0.40 |
| Williams %R (15m to daily) (`willr`) | Elder-Ray (1h to daily) (`elder`) | 0.73 | reads nearly alike | 0.55 |
| Intraday levels (VWAP and opening range) (`intraday`) | Pivot points (daily and weekly) (`pivots`) | 0.73 | reads nearly alike | 0.44 |
| Elder-Ray (1h to daily) (`elder`) | Pivot points (daily and weekly) (`pivots`) | 0.72 | reads nearly alike | 0.35 |
| Intraday levels (VWAP and opening range) (`intraday`) | Kaufman adaptive average (KAMA) (`kama`) | 0.71 | reads nearly alike | 0.25 |
| Moving averages (SMA and EMA 5-200) (`mavg`) | Williams %R (15m to daily) (`willr`) | 0.71 | reads nearly alike | 0.38 |
| StochRSI (15m to daily) (`stochrsi`) | CCI (15m to daily) (`cci`) | 0.71 | reads nearly alike | 0.47 |
| Intraday levels (VWAP and opening range) (`intraday`) | Moving-average ribbon (`ribbon`) | 0.71 | reads nearly alike | 0.35 |
| Ichimoku cloud (`ichimoku`) | CCI (15m to daily) (`cci`) | 0.71 | reads nearly alike | 0.34 |
| Ichimoku cloud (`ichimoku`) | Elder-Ray (1h to daily) (`elder`) | 0.71 | reads nearly alike | 0.31 |

## 3. Cards whose readings are contained in another card (R(A in B) at or above 0.85 in both halves)

| card A | is contained in card B | R(A in B) | groups |
|---|---|---|---|
| StochRSI (15m to daily) (`stochrsi`) | Momentum and stretch: Stretch and exhaustion (`meanrev`) | 0.91 | 4 |
| Timeframe strength (`trend`) | Moving averages (SMA and EMA 5-200) (`mavg`) | 0.90 | 4 |
| CCI (15m to daily) (`cci`) | Williams %R (15m to daily) (`willr`) | 0.88 | 4 |
| Williams %R (15m to daily) (`willr`) | CCI (15m to daily) (`cci`) | 0.88 | 4 |
| Elder-Ray (1h to daily) (`elder`) | CCI (15m to daily) (`cci`) | 0.88 | 4 |
| Kaufman adaptive average (KAMA) (`kama`) | CCI (15m to daily) (`cci`) | 0.87 | 4 |
| Kaufman adaptive average (KAMA) (`kama`) | Moving-average ribbon (`ribbon`) | 0.85 | 4 |

## 4. Clusters across the groups

**Pull overlap, threshold 0.85 (duplicates): 0 clusters**


**Pull overlap, threshold 0.70 (near-duplicates): 2 clusters**

1. Momentum and stretch: Momentum (`momentum`); Order flow (CVD) (`flow`)
   - crypto: best rated Momentum and stretch: Momentum (rank 4, worse half 53.9%; halves 55.7 / 53.9, with)
2. Momentum and stretch: Stretch and exhaustion (`meanrev`); StochRSI (15m to daily) (`stochrsi`)
   - crypto: best rated Momentum and stretch: Stretch and exhaustion (rank 4, worse half 53.9%; halves 55.7 / 53.9, with)
   - metals: best rated Momentum and stretch: Stretch and exhaustion (rank 12, worse half 51.7%; halves 53.0 / 51.7, with)
   - fx: best rated Momentum and stretch: Stretch and exhaustion (rank 4, worse half 52.5%; halves 52.7 / 52.5, with)
   - energy: best rated Momentum and stretch: Stretch and exhaustion (rank 13, worse half 51.3%; halves 51.3 / 51.5, with)

**Reading overlap, threshold 0.85 (reads alike): 1 cluster**

1. CCI (15m to daily) (`cci`); Williams %R (15m to daily) (`willr`)
   - crypto: best rated CCI (15m to daily) (rank 12, worse half 53.2%; halves 54.5 / 53.2, with)
   - metals: best rated CCI (15m to daily) (rank 6, worse half 52.1%; halves 52.1 / 52.3, with)
   - fx: best rated CCI (15m to daily) (rank 31, worse half 50.5%; halves 52.9 / 50.5, with)
   - energy: best rated Williams %R (15m to daily) (rank 20, worse half 51.0%; halves 49.0 / 47.6, against)

**Reading overlap, threshold 0.70 (reads nearly alike): 3 clusters**

1. Timeframe strength (`trend`); Moving averages (SMA and EMA 5-200) (`mavg`)
   - crypto: best rated Moving averages (SMA and EMA 5-200) (rank 19, worse half 52.5%; halves 56.3 / 52.5, with)
   - metals: best rated Moving averages (SMA and EMA 5-200) (rank 31, worse half 50.9%; halves 50.9 / 51.0, with)
   - fx: best rated Timeframe strength (rank 16, worse half 51.7%; halves 51.7 / 56.1, with)
   - energy: best rated Moving averages (SMA and EMA 5-200) (rank 9, worse half 51.8%; halves 51.8 / 52.0, with)
2. Momentum and stretch: Stretch and exhaustion (`meanrev`); Moving-average ribbon (`ribbon`); Kaufman adaptive average (KAMA) (`kama`); StochRSI (15m to daily) (`stochrsi`); CCI (15m to daily) (`cci`); Williams %R (15m to daily) (`willr`); Elder-Ray (1h to daily) (`elder`)
   - crypto: best rated Moving-average ribbon (rank 2, worse half 54.4%; halves 54.4 / 54.6, with)
   - metals: best rated Elder-Ray (1h to daily) (rank 5, worse half 52.3%; halves 52.3 / 52.5, with)
   - fx: best rated Momentum and stretch: Stretch and exhaustion (rank 4, worse half 52.5%; halves 52.7 / 52.5, with)
   - energy: best rated Elder-Ray (1h to daily) (rank 7, worse half 52.0%; halves 52.7 / 52.0, with)
3. Intraday levels (VWAP and opening range) (`intraday`); Volume profile (session and 7 days) (`vprofile`)
   - crypto: best rated Volume profile (session and 7 days) (rank 17, worse half 52.8%; halves 52.8 / 54.0, with)
   - metals: best rated Volume profile (session and 7 days) (rank 33, worse half 50.7%; halves 53.7 / 50.7, with)
   - energy: best rated Intraday levels (VWAP and opening range) (rank 33, worse half 50.6%; halves 50.6 / 50.9, with)

## 5. Per market group: clusters among its cards, and how much of the vote each holds

Share of the say = the engine's voting weights on this history (trust over all voices, the group's voters only, the 40% cap, the silent-voice rule), mean over the sessions of each half. "Voters" excludes the owner's voice.

### crypto (BTCUSDT, ETHUSDT): 60 cards measured, 12 voters

Voters and their share of the say (1st half / 2nd half): Timeframe strength 7% / 7%; Regime 6% / 5%; Support and resistance 10% / 9%; Momentum and stretch: Momentum 8% / 8%; Momentum and stretch: Stretch and exhaustion 10% / 9%; Momentum and stretch: Pullback inside the trend 8% / 8%; Order flow (CVD) 7% / 7%; Working strategies 8% / 9%; Perp basis and premium 8% / 7%; Stablecoin supply 8% / 7%; Coinbase premium 10% / 14%; Market breadth and ETH/BTC 11% / 10%.

**Pull overlap >= 0.85: 0 clusters, 0 holding two or more voters**

**Pull overlap >= 0.70: 4 clusters, 1 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Timeframe strength (votes); CCI (15m to daily); Williams %R (15m to daily); Elder-Ray (1h to daily); Linear-regression channel (1h to daily) | Timeframe strength | 1 of 12 | 7% / 7% | Linear-regression channel (1h to daily) (rank 11, 53.3%) |
| 2 | Momentum and stretch: Momentum (votes); Order flow (CVD) (votes) | Momentum and stretch: Momentum, Order flow (CVD) | 2 of 12 | 15% / 14% | Momentum and stretch: Momentum (rank 4, 53.9%) |
| 3 | Momentum and stretch: Pullback inside the trend (votes); StochRSI (15m to daily) | Momentum and stretch: Pullback inside the trend | 1 of 12 | 8% / 8% | Momentum and stretch: Pullback inside the trend (rank 4, 53.9%) |
| 4 | Intraday levels (VWAP and opening range); Volume profile (session and 7 days); Daily range budget and range breaks | - | 0 of 12 | 0% / 0% | Volume profile (session and 7 days) (rank 17, 52.8%) |

**Reading overlap >= 0.85: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | CCI (15m to daily); Williams %R (15m to daily) | - | 0 of 12 | 0% / 0% | CCI (15m to daily) (rank 12, 53.2%) |

**Reading overlap >= 0.70: 4 clusters, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Timeframe strength (votes); Moving averages (SMA and EMA 5-200) | Timeframe strength | 1 of 12 | 7% / 7% | Moving averages (SMA and EMA 5-200) (rank 19, 52.5%) |
| 2 | Momentum and stretch: Stretch and exhaustion (votes); StochRSI (15m to daily) | Momentum and stretch: Stretch and exhaustion | 1 of 12 | 10% / 9% | Momentum and stretch: Stretch and exhaustion (rank 4, 53.9%) |
| 3 | Intraday levels (VWAP and opening range); Volume profile (session and 7 days) | - | 0 of 12 | 0% / 0% | Volume profile (session and 7 days) (rank 17, 52.8%) |
| 4 | Moving-average ribbon; Kaufman adaptive average (KAMA); CCI (15m to daily); Williams %R (15m to daily); Elder-Ray (1h to daily) | - | 0 of 12 | 0% / 0% | Moving-average ribbon (rank 2, 54.4%) |

Separate voting ideas: 12 voters make 11 separate ideas at the near-duplicate threshold (12 at the duplicate threshold).

Voter against voter, pull overlap 1st / 2nd half:

| | `trend` | `regime` | `levels` | `momentum` | `meanrev` | `pullback` | `flow` | `strategies` | `basis` | `stable` | `cbprem` | `breadth` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `trend` |  | 0.08 / -0.01 | 0.40 / 0.58 | 0.62 / 0.74 | 0.55 / 0.72 | 0.45 / 0.49 | 0.54 / 0.66 | 0.13 / 0.24 | 0.21 / -0.08 | -0.16 / 0.09 | 0.16 / 0.25 | 0.39 / 0.39 |
| `regime` | 0.08 / -0.01 |  | 0.09 / 0.04 | 0.05 / 0.05 | 0.03 / 0.01 | 0.02 / -0.03 | -0.05 / 0.01 | 0.15 / 0.07 | 0.06 / 0.04 | -0.05 / 0.01 | -0.05 / 0.05 | 0.05 / -0.03 |
| `levels` | 0.40 / 0.58 | 0.09 / 0.04 |  | 0.39 / 0.46 | 0.37 / 0.44 | 0.16 / 0.28 | 0.32 / 0.41 | 0.07 / 0.12 | 0.01 / -0.01 | 0.15 / -0.03 | 0.09 / 0.17 | 0.23 / 0.24 |
| `momentum` | 0.62 / 0.74 | 0.05 / 0.05 | 0.39 / 0.46 |  | 0.67 / 0.71 | 0.34 / 0.44 | 0.73 / 0.75 | 0.12 / 0.32 | -0.06 / -0.14 | 0.04 / 0.15 | 0.23 / 0.28 | 0.40 / 0.34 |
| `meanrev` | 0.55 / 0.72 | 0.03 / 0.01 | 0.37 / 0.44 | 0.67 / 0.71 |  | 0.54 / 0.63 | 0.58 / 0.63 | 0.10 / 0.22 | 0.01 / -0.09 | -0.02 / 0.07 | 0.16 / 0.20 | 0.32 / 0.33 |
| `pullback` | 0.45 / 0.49 | 0.02 / -0.03 | 0.16 / 0.28 | 0.34 / 0.44 | 0.54 / 0.63 |  | 0.44 / 0.53 | 0.03 / 0.07 | 0.07 / -0.07 | -0.07 / 0.07 | 0.06 / 0.10 | 0.12 / 0.23 |
| `flow` | 0.54 / 0.66 | -0.05 / 0.01 | 0.32 / 0.41 | 0.73 / 0.75 | 0.58 / 0.63 | 0.44 / 0.53 |  | 0.05 / 0.08 | -0.07 / -0.03 | -0.02 / 0.04 | 0.16 / 0.12 | 0.23 / 0.23 |
| `strategies` | 0.13 / 0.24 | 0.15 / 0.07 | 0.07 / 0.12 | 0.12 / 0.32 | 0.10 / 0.22 | 0.03 / 0.07 | 0.05 / 0.08 |  | -0.12 / -0.16 | -0.23 / 0.21 | 0.08 / 0.13 | 0.15 / 0.11 |
| `basis` | 0.21 / -0.08 | 0.06 / 0.04 | 0.01 / -0.01 | -0.06 / -0.14 | 0.01 / -0.09 | 0.07 / -0.07 | -0.07 / -0.03 | -0.12 / -0.16 |  | -0.19 / -0.22 | -0.04 / -0.01 | -0.06 / -0.03 |
| `stable` | -0.16 / 0.09 | -0.05 / 0.01 | 0.15 / -0.03 | 0.04 / 0.15 | -0.02 / 0.07 | -0.07 / 0.07 | -0.02 / 0.04 | -0.23 / 0.21 | -0.19 / -0.22 |  | -0.09 / 0.23 | 0.15 / 0.06 |
| `cbprem` | 0.16 / 0.25 | -0.05 / 0.05 | 0.09 / 0.17 | 0.23 / 0.28 | 0.16 / 0.20 | 0.06 / 0.10 | 0.16 / 0.12 | 0.08 / 0.13 | -0.04 / -0.01 | -0.09 / 0.23 |  | 0.14 / 0.25 |
| `breadth` | 0.39 / 0.39 | 0.05 / -0.03 | 0.23 / 0.24 | 0.40 / 0.34 | 0.32 / 0.33 | 0.12 / 0.23 | 0.23 / 0.23 | 0.15 / 0.11 | -0.06 / -0.03 | 0.15 / 0.06 | 0.14 / 0.25 |  |

Left out of this group: `book` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/0, ETHUSDT 0/0)); `cot` (does not apply to this market); `earnings` (does not apply to this market); `eia` (does not apply to this market); `eqbreadth` (does not apply to this market); `etf` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/62833, ETHUSDT 0/44305)); `goldetf` (does not apply to this market); `japan` (does not apply to this market); `kronos` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/0, ETHUSDT 0/0)); `liq` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/0, ETHUSDT 0/0)); `lsratio` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/0, ETHUSDT 0/0)); `metals` (does not apply to this market); `news` (speaks on fewer than 2000 sessions in a half (BTCUSDT 0/0, ETHUSDT 0/0)); `oilpos` (does not apply to this market); `oilspread` (does not apply to this market); `oilvol` (does not apply to this market); `opec` (does not apply to this market); `overnight` (does not apply to this market); `putcall` (does not apply to this market); `rates` (does not apply to this market); `volx` (does not apply to this market).

### metals (XAUUSD, XAGUSD): 47 cards measured, 13 voters

Voters and their share of the say (1st half / 2nd half): Timeframe strength 7% / 8%; Regime 7% / 6%; Momentum and stretch: Momentum 7% / 7%; Momentum and stretch: Stretch and exhaustion 8% / 8%; Momentum and stretch: Pullback inside the trend 7% / 7%; `news` 0% / 0%; News and economic events: Economic calendar and macro tape 10% / 11%; Market structure 8% / 8%; Volatility gauges 10% / 10%; Gold and silver ETF holdings 9% / 11%; Moving averages (SMA and EMA 5-200) 7% / 9%; Ichimoku cloud 10% / 8%; Kaufman adaptive average (KAMA) 8% / 8%.

**Pull overlap >= 0.85: 0 clusters, 0 holding two or more voters**

**Pull overlap >= 0.70: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Momentum and stretch: Stretch and exhaustion (votes); StochRSI (15m to daily) | Momentum and stretch: Stretch and exhaustion | 1 of 13 | 8% / 8% | Momentum and stretch: Stretch and exhaustion (rank 12, 51.7%) |

**Reading overlap >= 0.85: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | CCI (15m to daily); Williams %R (15m to daily) | - | 0 of 13 | 0% / 0% | CCI (15m to daily) (rank 6, 52.1%) |

**Reading overlap >= 0.70: 3 clusters, 2 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Timeframe strength (votes); Moving averages (SMA and EMA 5-200) (votes) | Timeframe strength, Moving averages (SMA and EMA 5-200) | 2 of 13 | 15% / 16% | Moving averages (SMA and EMA 5-200) (rank 31, 50.9%) |
| 2 | Momentum and stretch: Momentum (votes); Momentum and stretch: Stretch and exhaustion (votes); Moving-average ribbon; Kaufman adaptive average (KAMA) (votes); StochRSI (15m to daily); CCI (15m to daily); Williams %R (15m to daily); Elder-Ray (1h to daily) | Momentum and stretch: Momentum, Momentum and stretch: Stretch and exhaustion, Kaufman adaptive average (KAMA) | 3 of 13 | 23% / 23% | Elder-Ray (1h to daily) (rank 5, 52.3%) |
| 3 | Intraday levels (VWAP and opening range); Volume profile (session and 7 days); Pivot points (daily and weekly) | - | 0 of 13 | 0% / 0% | Pivot points (daily and weekly) (rank 7, 52.0%) |

Separate voting ideas: 13 voters make 13 separate ideas at the near-duplicate threshold (13 at the duplicate threshold).

Voter against voter, pull overlap 1st / 2nd half:

| | `trend` | `regime` | `momentum` | `meanrev` | `pullback` | `macro` | `structure` | `volx` | `goldetf` | `mavg` | `ichimoku` | `kama` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `trend` |  | -0.04 / 0.19 | 0.26 / 0.61 | 0.40 / 0.42 | 0.44 / 0.05 | 0.04 / 0.05 | 0.25 / 0.28 | -0.01 / 0.12 | -0.03 / -0.08 | 0.64 / 0.52 | 0.30 / 0.50 | 0.27 / 0.36 |
| `regime` | -0.04 / 0.19 |  | 0.00 / 0.03 | 0.00 / -0.04 | -0.10 / 0.02 | -0.10 / -0.05 | 0.01 / 0.02 | 0.05 / 0.15 | -0.03 / -0.01 | -0.04 / 0.11 | -0.07 / -0.02 | -0.00 / -0.00 |
| `momentum` | 0.26 / 0.61 | 0.00 / 0.03 |  | 0.29 / 0.34 | 0.26 / 0.11 | 0.03 / 0.04 | 0.22 / 0.21 | -0.00 / 0.04 | -0.01 / -0.03 | 0.28 / 0.30 | 0.13 / 0.30 | 0.43 / 0.42 |
| `meanrev` | 0.40 / 0.42 | 0.00 / -0.04 | 0.29 / 0.34 |  | 0.52 / 0.33 | 0.01 / 0.08 | 0.29 / 0.16 | -0.04 / 0.05 | 0.06 / -0.04 | 0.33 / 0.39 | 0.28 / 0.54 | 0.42 / 0.16 |
| `pullback` | 0.44 / 0.05 | -0.10 / 0.02 | 0.26 / 0.11 | 0.52 / 0.33 |  | 0.04 / 0.06 | 0.20 / -0.03 | -0.02 / 0.14 | 0.09 / 0.06 | 0.38 / -0.02 | 0.18 / 0.20 | 0.27 / 0.03 |
| `macro` | 0.04 / 0.05 | -0.10 / -0.05 | 0.03 / 0.04 | 0.01 / 0.08 | 0.04 / 0.06 |  | 0.00 / 0.06 | 0.45 / 0.43 | 0.03 / 0.05 | 0.02 / 0.08 | 0.02 / 0.08 | 0.01 / 0.02 |
| `structure` | 0.25 / 0.28 | 0.01 / 0.02 | 0.22 / 0.21 | 0.29 / 0.16 | 0.20 / -0.03 | 0.00 / 0.06 |  | 0.01 / 0.05 | -0.06 / -0.07 | 0.21 / 0.35 | 0.13 / 0.30 | 0.24 / 0.08 |
| `volx` | -0.01 / 0.12 | 0.05 / 0.15 | -0.00 / 0.04 | -0.04 / 0.05 | -0.02 / 0.14 | 0.45 / 0.43 | 0.01 / 0.05 |  | 0.03 / 0.12 | 0.01 / 0.13 | -0.06 / 0.08 | -0.01 / 0.03 |
| `goldetf` | -0.03 / -0.08 | -0.03 / -0.01 | -0.01 / -0.03 | 0.06 / -0.04 | 0.09 / 0.06 | 0.03 / 0.05 | -0.06 / -0.07 | 0.03 / 0.12 |  | 0.08 / -0.10 | 0.04 / -0.08 | -0.03 / -0.01 |
| `mavg` | 0.64 / 0.52 | -0.04 / 0.11 | 0.28 / 0.30 | 0.33 / 0.39 | 0.38 / -0.02 | 0.02 / 0.08 | 0.21 / 0.35 | 0.01 / 0.13 | 0.08 / -0.10 |  | 0.34 / 0.54 | 0.23 / 0.12 |
| `ichimoku` | 0.30 / 0.50 | -0.07 / -0.02 | 0.13 / 0.30 | 0.28 / 0.54 | 0.18 / 0.20 | 0.02 / 0.08 | 0.13 / 0.30 | -0.06 / 0.08 | 0.04 / -0.08 | 0.34 / 0.54 |  | 0.15 / 0.13 |
| `kama` | 0.27 / 0.36 | -0.00 / -0.00 | 0.43 / 0.42 | 0.42 / 0.16 | 0.27 / 0.03 | 0.01 / 0.02 | 0.24 / 0.08 | -0.01 / 0.03 | -0.03 / -0.01 | 0.23 / 0.12 | 0.15 / 0.13 |  |

Voters not measured here: news (speaks on fewer than 2000 sessions in a half (XAUUSD 0/0, XAGUSD 0/0)).

Left out of this group: `basis` (does not apply to this market); `bitfinex` (does not apply to this market); `book` (does not apply to this market); `breadth` (does not apply to this market); `cbprem` (does not apply to this market); `cme` (does not apply to this market); `cmegap` (does not apply to this market); `dom` (does not apply to this market); `earnings` (does not apply to this market); `eia` (does not apply to this market); `eqbreadth` (does not apply to this market); `etf` (does not apply to this market); `flow` (does not apply to this market); `funding` (does not apply to this market); `japan` (does not apply to this market); `kprem` (does not apply to this market); `kronos` (speaks on fewer than 2000 sessions in a half (XAUUSD 0/0, XAGUSD 0/0)); `liq` (does not apply to this market); `lsratio` (does not apply to this market); `metrics` (does not apply to this market); `news` (speaks on fewer than 2000 sessions in a half (XAUUSD 0/0, XAGUSD 0/0)); `oilpos` (does not apply to this market); `oilspread` (does not apply to this market); `oilvol` (does not apply to this market); `onchain` (does not apply to this market); `opec` (does not apply to this market); `optflow` (does not apply to this market); `options` (does not apply to this market); `overnight` (does not apply to this market); `putcall` (does not apply to this market); `sentiment` (does not apply to this market); `spotlead` (does not apply to this market); `stable` (does not apply to this market); `xfund` (does not apply to this market).

### fx (USDJPY): 42 cards measured, 12 voters

Voters and their share of the say (1st half / 2nd half): Timeframe strength 8% / 9%; Regime 6% / 5%; Support and resistance 8% / 9%; Momentum and stretch: Momentum 8% / 9%; Momentum and stretch: Stretch and exhaustion 10% / 9%; Momentum and stretch: Pullback inside the trend 8% / 9%; Working strategies 11% / 9%; Time and session 9% / 12%; Trade setups 3% / 3%; Trend quality and squeeze 10% / 10%; Rates and the dollar 9% / 9%; Moving averages (SMA and EMA 5-200) 9% / 9%.

**Pull overlap >= 0.85: 0 clusters, 0 holding two or more voters**

**Pull overlap >= 0.70: 3 clusters, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Momentum and stretch: Stretch and exhaustion (votes); StochRSI (15m to daily) | Momentum and stretch: Stretch and exhaustion | 1 of 12 | 10% / 9% | Momentum and stretch: Stretch and exhaustion (rank 4, 52.5%) |
| 2 | News and economic events: Economic calendar and macro tape; Rates and the dollar (votes) | Rates and the dollar | 1 of 12 | 9% / 9% | Rates and the dollar (rank 30, 50.5%) |
| 3 | Moving-average ribbon; CCI (15m to daily); Williams %R (15m to daily) | - | 0 of 12 | 0% / 0% | Moving-average ribbon (rank 23, 51.0%) |

**Reading overlap >= 0.85: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | CCI (15m to daily); Williams %R (15m to daily) | - | 0 of 12 | 0% / 0% | CCI (15m to daily) (rank 31, 50.5%) |

**Reading overlap >= 0.70: 4 clusters, 2 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Timeframe strength (votes); Moving averages (SMA and EMA 5-200) (votes) | Timeframe strength, Moving averages (SMA and EMA 5-200) | 2 of 12 | 17% / 18% | Timeframe strength (rank 16, 51.7%) |
| 2 | Momentum and stretch: Momentum (votes); Momentum and stretch: Stretch and exhaustion (votes); Moving-average ribbon; Kaufman adaptive average (KAMA); StochRSI (15m to daily); CCI (15m to daily); Williams %R (15m to daily); Elder-Ray (1h to daily) | Momentum and stretch: Momentum, Momentum and stretch: Stretch and exhaustion | 2 of 12 | 18% / 18% | Momentum and stretch: Momentum (rank 4, 52.5%) |
| 3 | Intraday levels (VWAP and opening range); Pivot points (daily and weekly) | - | 0 of 12 | 0% / 0% | Intraday levels (VWAP and opening range) (rank 7, 52.1%) |
| 4 | Aroon and Vortex (1h to daily); TRIX (1h to daily) | - | 0 of 12 | 0% / 0% | Aroon and Vortex (1h to daily) (rank 13, 52.0%) |

Separate voting ideas: 12 voters make 12 separate ideas at the near-duplicate threshold (12 at the duplicate threshold).

Voter against voter, pull overlap 1st / 2nd half:

| | `trend` | `regime` | `levels` | `momentum` | `meanrev` | `pullback` | `strategies` | `clock` | `setups` | `trendq` | `rates` | `mavg` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `trend` |  | -0.20 / -0.10 | 0.42 / 0.16 | 0.47 / 0.70 | 0.48 / 0.71 | 0.53 / 0.57 | 0.37 / -0.03 | 0.11 / 0.04 | 0.40 / 0.64 | 0.29 / 0.53 | -0.16 / -0.04 | 0.70 / 0.61 |
| `regime` | -0.20 / -0.10 |  | -0.09 / 0.09 | -0.02 / -0.01 | 0.03 / -0.04 | -0.11 / -0.05 | -0.40 / -0.08 | -0.16 / 0.03 | 0.05 / -0.04 | 0.10 / -0.03 | 0.22 / 0.16 | 0.07 / -0.02 |
| `levels` | 0.42 / 0.16 | -0.09 / 0.09 |  | 0.26 / 0.16 | 0.28 / 0.13 | 0.23 / 0.10 | 0.20 / -0.07 | 0.13 / 0.16 | 0.36 / 0.28 | 0.20 / 0.13 | -0.06 / 0.02 | 0.29 / 0.11 |
| `momentum` | 0.47 / 0.70 | -0.02 / -0.01 | 0.26 / 0.16 |  | 0.48 / 0.54 | 0.36 / 0.38 | -0.05 / -0.26 | 0.01 / 0.01 | 0.48 / 0.57 | 0.37 / 0.47 | -0.00 / 0.15 | 0.49 / 0.48 |
| `meanrev` | 0.48 / 0.71 | 0.03 / -0.04 | 0.28 / 0.13 | 0.48 / 0.54 |  | 0.66 / 0.82 | -0.03 / 0.02 | -0.02 / 0.02 | 0.61 / 0.66 | 0.60 / 0.54 | -0.01 / -0.01 | 0.50 / 0.61 |
| `pullback` | 0.53 / 0.57 | -0.11 / -0.05 | 0.23 / 0.10 | 0.36 / 0.38 | 0.66 / 0.82 |  | 0.19 / 0.03 | 0.04 / 0.02 | 0.53 / 0.66 | 0.45 / 0.47 | -0.12 / -0.03 | 0.50 / 0.60 |
| `strategies` | 0.37 / -0.03 | -0.40 / -0.08 | 0.20 / -0.07 | -0.05 / -0.26 | -0.03 / 0.02 | 0.19 / 0.03 |  | 0.15 / 0.01 | -0.10 / -0.13 | -0.08 / -0.05 | -0.20 / -0.24 | 0.15 / 0.02 |
| `clock` | 0.11 / 0.04 | -0.16 / 0.03 | 0.13 / 0.16 | 0.01 / 0.01 | -0.02 / 0.02 | 0.04 / 0.02 | 0.15 / 0.01 |  | -0.02 / 0.02 | -0.01 / 0.08 | -0.02 / 0.03 | 0.01 / 0.02 |
| `setups` | 0.40 / 0.64 | 0.05 / -0.04 | 0.36 / 0.28 | 0.48 / 0.57 | 0.61 / 0.66 | 0.53 / 0.66 | -0.10 / -0.13 | -0.02 / 0.02 |  | 0.52 / 0.51 | 0.05 / 0.00 | 0.45 / 0.58 |
| `trendq` | 0.29 / 0.53 | 0.10 / -0.03 | 0.20 / 0.13 | 0.37 / 0.47 | 0.60 / 0.54 | 0.45 / 0.47 | -0.08 / -0.05 | -0.01 / 0.08 | 0.52 / 0.51 |  | 0.00 / -0.12 | 0.36 / 0.44 |
| `rates` | -0.16 / -0.04 | 0.22 / 0.16 | -0.06 / 0.02 | -0.00 / 0.15 | -0.01 / -0.01 | -0.12 / -0.03 | -0.20 / -0.24 | -0.02 / 0.03 | 0.05 / 0.00 | 0.00 / -0.12 |  | -0.10 / -0.06 |
| `mavg` | 0.70 / 0.61 | 0.07 / -0.02 | 0.29 / 0.11 | 0.49 / 0.48 | 0.50 / 0.61 | 0.50 / 0.60 | 0.15 / 0.02 | 0.01 / 0.02 | 0.45 / 0.58 | 0.36 / 0.44 | -0.10 / -0.06 |  |

Left out of this group: `basis` (does not apply to this market); `bitfinex` (does not apply to this market); `book` (does not apply to this market); `breadth` (does not apply to this market); `cbprem` (does not apply to this market); `cme` (does not apply to this market); `cmegap` (does not apply to this market); `cmf` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `cross` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `dom` (does not apply to this market); `earnings` (does not apply to this market); `eia` (does not apply to this market); `eqbreadth` (does not apply to this market); `etf` (does not apply to this market); `flow` (does not apply to this market); `funding` (does not apply to this market); `goldetf` (does not apply to this market); `kprem` (does not apply to this market); `kronos` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `liq` (does not apply to this market); `lsratio` (does not apply to this market); `metals` (does not apply to this market); `metrics` (does not apply to this market); `mfi` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `news` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `oilpos` (does not apply to this market); `oilspread` (does not apply to this market); `oilvol` (does not apply to this market); `onchain` (does not apply to this market); `opec` (does not apply to this market); `optflow` (does not apply to this market); `options` (does not apply to this market); `overnight` (does not apply to this market); `putcall` (does not apply to this market); `sentiment` (does not apply to this market); `spotlead` (does not apply to this market); `stable` (does not apply to this market); `vprofile` (speaks on fewer than 2000 sessions in a half (USDJPY 0/0)); `xfund` (does not apply to this market).

### energy (WTI, BRENT): 47 cards measured, 10 voters

Voters and their share of the say (1st half / 2nd half): Regime 9% / 8%; Support and resistance 15% / 13%; Trade setups 3% / 3%; Trend quality and squeeze 12% / 10%; Candle size and realistic targets 9% / 9%; Fibonacci retracement 11% / 10%; Moving averages (SMA and EMA 5-200) 10% / 10%; Kaufman adaptive average (KAMA) 11% / 15%; Oil volatility 11% / 12%; WTI-Brent and curve 9% / 9%.

**Pull overlap >= 0.85: 0 clusters, 0 holding two or more voters**

**Pull overlap >= 0.70: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Momentum and stretch: Stretch and exhaustion; StochRSI (15m to daily) | - | 0 of 10 | 0% / 0% | Momentum and stretch: Stretch and exhaustion (rank 13, 51.3%) |

**Reading overlap >= 0.85: 1 cluster, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | CCI (15m to daily); Williams %R (15m to daily) | - | 0 of 10 | 0% / 0% | Williams %R (15m to daily) (rank 20, 51.0%) |

**Reading overlap >= 0.70: 5 clusters, 0 holding two or more voters**

| cluster | cards | voters in it | share of voters | share of the say (1st / 2nd) | best rated |
|---|---|---|---|---|---|
| 1 | Timeframe strength; The other coin; Moving averages (SMA and EMA 5-200) (votes) | Moving averages (SMA and EMA 5-200) | 1 of 10 | 10% / 10% | Moving averages (SMA and EMA 5-200) (rank 9, 51.8%) |
| 2 | Momentum and stretch: Momentum; Momentum and stretch: Stretch and exhaustion; Moving-average ribbon; Kaufman adaptive average (KAMA) (votes); StochRSI (15m to daily); CCI (15m to daily); Williams %R (15m to daily); Elder-Ray (1h to daily) | Kaufman adaptive average (KAMA) | 1 of 10 | 11% / 15% | Elder-Ray (1h to daily) (rank 7, 52.0%) |
| 3 | Intraday levels (VWAP and opening range); Volume profile (session and 7 days) | - | 0 of 10 | 0% / 0% | Intraday levels (VWAP and opening range) (rank 33, 50.6%) |
| 4 | Ichimoku cloud; Pivot points (daily and weekly) | - | 0 of 10 | 0% / 0% | Pivot points (daily and weekly) (rank 5, 52.7%) |
| 5 | Aroon and Vortex (1h to daily); TRIX (1h to daily) | - | 0 of 10 | 0% / 0% | Aroon and Vortex (1h to daily) (rank 8, 52.0%) |

Separate voting ideas: 10 voters make 10 separate ideas at the near-duplicate threshold (10 at the duplicate threshold).

Voter against voter, pull overlap 1st / 2nd half:

| | `regime` | `levels` | `setups` | `trendq` | `candles` | `fib` | `mavg` | `kama` | `oilvol` | `oilspread` |
|---|---|---|---|---|---|---|---|---|---|---|
| `regime` |  | -0.47 / -0.47 | 0.08 / 0.09 | -0.05 / 0.04 | 0.09 / 0.16 | 0.05 / -0.04 | 0.11 / 0.06 | 0.05 / -0.05 | 0.15 / 0.14 | 0.29 / 0.05 |
| `levels` | -0.47 / -0.47 |  | 0.07 / 0.09 | 0.12 / -0.01 | -0.22 / -0.15 | 0.03 / 0.05 | -0.27 / -0.05 | 0.09 / 0.06 | -0.19 / -0.07 | -0.35 / -0.03 |
| `setups` | 0.08 / 0.09 | 0.07 / 0.09 |  | 0.14 / 0.18 | -0.02 / -0.07 | 0.08 / 0.01 | -0.05 / -0.19 | 0.14 / 0.12 | -0.00 / 0.07 | 0.02 / -0.00 |
| `trendq` | -0.05 / 0.04 | 0.12 / -0.01 | 0.14 / 0.18 |  | -0.03 / -0.01 | 0.14 / 0.03 | 0.17 / 0.19 | 0.50 / 0.23 | 0.01 / -0.04 | 0.01 / 0.00 |
| `candles` | 0.09 / 0.16 | -0.22 / -0.15 | -0.02 / -0.07 | -0.03 / -0.01 |  | 0.04 / -0.04 | 0.19 / 0.05 | 0.01 / -0.04 | 0.09 / -0.11 | 0.18 / 0.00 |
| `fib` | 0.05 / -0.04 | 0.03 / 0.05 | 0.08 / 0.01 | 0.14 / 0.03 | 0.04 / -0.04 |  | 0.15 / 0.12 | 0.14 / 0.08 | 0.04 / -0.01 | 0.04 / 0.01 |
| `mavg` | 0.11 / 0.06 | -0.27 / -0.05 | -0.05 / -0.19 | 0.17 / 0.19 | 0.19 / 0.05 | 0.15 / 0.12 |  | 0.28 / 0.20 | 0.31 / -0.11 | 0.17 / 0.03 |
| `kama` | 0.05 / -0.05 | 0.09 / 0.06 | 0.14 / 0.12 | 0.50 / 0.23 | 0.01 / -0.04 | 0.14 / 0.08 | 0.28 / 0.20 |  | 0.02 / -0.04 | 0.04 / 0.02 |
| `oilvol` | 0.15 / 0.14 | -0.19 / -0.07 | -0.00 / 0.07 | 0.01 / -0.04 | 0.09 / -0.11 | 0.04 / -0.01 | 0.31 / -0.11 | 0.02 / -0.04 |  | -0.01 / -0.00 |
| `oilspread` | 0.29 / 0.05 | -0.35 / -0.03 | 0.02 / -0.00 | 0.01 / 0.00 | 0.18 / 0.00 | 0.04 / 0.01 | 0.17 / 0.03 | 0.04 / 0.02 | -0.01 / -0.00 |  |

Left out of this group: `basis` (does not apply to this market); `bitfinex` (does not apply to this market); `book` (does not apply to this market); `breadth` (does not apply to this market); `cbprem` (does not apply to this market); `cme` (does not apply to this market); `cmegap` (does not apply to this market); `cot` (does not apply to this market); `dom` (does not apply to this market); `earnings` (does not apply to this market); `eqbreadth` (does not apply to this market); `etf` (does not apply to this market); `flow` (does not apply to this market); `funding` (does not apply to this market); `goldetf` (does not apply to this market); `japan` (does not apply to this market); `kprem` (does not apply to this market); `kronos` (speaks on fewer than 2000 sessions in a half (WTI 0/0, BRENT 0/0)); `liq` (does not apply to this market); `lsratio` (does not apply to this market); `metals` (does not apply to this market); `metrics` (does not apply to this market); `news` (speaks on fewer than 2000 sessions in a half (WTI 0/0, BRENT 0/0)); `onchain` (does not apply to this market); `optflow` (does not apply to this market); `options` (does not apply to this market); `overnight` (does not apply to this market); `putcall` (does not apply to this market); `rates` (does not apply to this market); `sentiment` (does not apply to this market); `spotlead` (does not apply to this market); `stable` (does not apply to this market); `volx` (does not apply to this market); `xfund` (does not apply to this market).

## 6. Context: how hard each card pulls and how often it speaks

Mean |pull| in points (P(up) - P(down), x100) on the sessions where the card speaks, 1st / 2nd half; a card whose pull is a fraction of a point barely moves the odds whatever it overlaps with.

| card | crypto | metals | fx | energy |
|---|---|---|---|---|
| Timeframe strength (`trend`) | 3.96 / 3.20 (votes) | 2.21 / 1.68 (votes) | 3.54 / 2.30 (votes) | 6.06 / 1.59 |
| Regime (`regime`) | 3.65 / 2.51 (votes) | 4.59 / 3.00 (votes) | 3.50 / 1.70 (votes) | 6.64 / 5.34 (votes) |
| Support and resistance (`levels`) | 11.05 / 8.60 (votes) | 4.19 / 3.06 | 4.15 / 3.14 (votes) | 17.47 / 16.88 (votes) |
| Momentum and stretch: Momentum (`momentum`) | 4.20 / 3.28 (votes) | 2.50 / 1.99 (votes) | 2.92 / 1.58 (votes) | 4.65 / 1.62 |
| Momentum and stretch: Stretch and exhaustion (`meanrev`) | 5.43 / 4.62 (votes) | 2.62 / 2.15 (votes) | 4.02 / 3.67 (votes) | 6.33 / 2.79 |
| Momentum and stretch: Pullback inside the trend (`pullback`) | 3.39 / 3.25 (votes) | 1.82 / 0.68 (votes) | 3.09 / 3.25 (votes) | 5.15 / 1.63 |
| Order flow (CVD) (`flow`) | 3.69 / 2.61 (votes) | - | - | - |
| Funding and positioning (`funding`) | 4.29 / 0.81 | - | - | - |
| Working strategies (`strategies`) | 3.77 / 3.56 (votes) | 5.86 / 3.62 | 5.13 / 1.09 (votes) | 8.73 / 1.91 |
| News and economic events: Economic calendar and macro tape (`macro`) | 3.54 / 2.70 | 4.42 / 2.67 (votes) | 3.46 / 2.08 | 3.29 / 2.31 |
| Risk and volatility (`risk`) | 1.21 / 1.19 | 2.16 / 1.39 | 2.23 / 1.09 | 4.30 / 1.27 |
| The other coin (`cross`) | 2.40 / 1.52 | 1.58 / 1.17 | - | 5.02 / 0.69 |
| Perp basis and premium (`basis`) | 3.41 / 1.06 (votes) | - | - | - |
| Options: implied volatility and skew (`options`) | 3.99 / 2.38 | - | - | - |
| Time and session (`clock`) | 4.69 / 2.58 | 4.65 / 4.68 | 4.95 / 5.16 (votes) | 5.25 / 4.95 |
| Stablecoin supply (`stable`) | 1.81 / 0.73 (votes) | - | - | - |
| Coinbase premium (`cbprem`) | 4.34 / 4.88 (votes) | - | - | - |
| Market breadth and ETH/BTC (`breadth`) | 4.74 / 3.87 (votes) | - | - | - |
| Fear and Greed (`sentiment`) | 2.00 / 1.37 | - | - | - |
| Market structure (`structure`) | 6.27 / 4.63 | 3.44 / 1.82 (votes) | 6.06 / 4.37 | 6.26 / 2.64 |
| Trade setups (`setups`) | 3.55 / 3.41 | 3.15 / 3.36 | 7.55 / 5.56 (votes) | 3.48 / 3.62 (votes) |
| Intraday levels (VWAP and opening range) (`intraday`) | 5.28 / 4.36 | 2.43 / 1.57 | 3.93 / 3.14 | 4.28 / 1.86 |
| Trend quality and squeeze (`trendq`) | 6.68 / 5.12 | 6.16 / 3.87 | 5.82 / 4.10 (votes) | 7.69 / 4.07 (votes) |
| Candle size and realistic targets (`candles`) | 2.42 / 1.44 | 2.95 / 1.02 | 4.15 / 2.31 | 3.40 / 1.17 (votes) |
| Fibonacci retracement (`fib`) | 3.46 / 2.76 | 2.96 / 1.51 | 4.18 / 2.75 | 3.53 / 2.14 (votes) |
| Volatility gauges (`volx`) | - | 4.95 / 2.60 (votes) | 3.66 / 2.94 | - |
| Rates and the dollar (`rates`) | - | 2.69 / 1.37 | 3.32 / 1.83 (votes) | - |
| Metals ratios (`metals`) | - | 3.38 / 2.84 | - | - |
| Gold and silver ETF holdings (`goldetf`) | - | 3.33 / 3.12 (votes) | - | - |
| Moving averages (SMA and EMA 5-200) (`mavg`) | 5.19 / 4.27 | 2.88 / 2.32 (votes) | 3.80 / 2.96 (votes) | 8.01 / 2.60 (votes) |
| Moving-average ribbon (`ribbon`) | 5.68 / 4.64 | 3.05 / 2.22 | 3.64 / 2.98 | 5.71 / 2.43 |
| Moving averages as support and resistance (`mavg_sr`) | 3.50 / 2.86 | 3.18 / 2.16 | 2.44 / 1.75 | 5.41 / 2.42 |
| Ichimoku cloud (`ichimoku`) | 6.04 / 4.98 | 4.24 / 2.59 (votes) | 4.11 / 3.49 | 7.10 / 2.73 |
| Hull moving average (`hull`) | 3.21 / 2.71 | 3.63 / 3.10 | 4.90 / 3.01 | 4.51 / 2.10 |
| Kaufman adaptive average (KAMA) (`kama`) | 4.44 / 4.41 | 2.77 / 2.49 (votes) | 3.60 / 3.31 | 4.75 / 3.63 (votes) |
| Futures positioning (CFTC) (`cot`) | - | 1.46 / 1.30 | 1.71 / 2.26 | - |
| Japan watch (`japan`) | - | - | 1.80 / 2.68 | - |
| EIA crude inventories (`eia`) | - | - | - | 9.72 / 2.35 |
| OPEC+ calendar (`opec`) | - | - | - | 1.95 / 2.25 |
| Oil volatility (`oilvol`) | - | - | - | 3.79 / 1.95 (votes) |
| Crude futures positioning (CFTC) (`oilpos`) | - | - | - | 1.87 / 2.08 |
| WTI-Brent and curve (`oilspread`) | - | - | - | 1.59 / 0.69 (votes) |
| Binance positioning (archive) (`metrics`) | 4.50 / 3.18 | - | - | - |
| Bitfinex margin positions (`bitfinex`) | 1.89 / 1.01 | - | - | - |
| CME futures positioning (CFTC) (`cme`) | 0.78 / 0.72 | - | - | - |
| On-chain activity and flows (`onchain`) | 2.60 / 0.78 | - | - | - |
| Supertrend (15m to daily) (`supertrend`) | 4.97 / 3.16 | 4.15 / 1.85 | 3.97 / 2.57 | 7.71 / 1.28 |
| StochRSI (15m to daily) (`stochrsi`) | 4.13 / 3.92 | 2.27 / 2.44 | 3.21 / 3.46 | 4.83 / 2.26 |
| Parabolic SAR (15m to daily) (`psar`) | 2.45 / 2.03 | 2.69 / 2.96 | 4.30 / 2.97 | 5.92 / 1.66 |
| Money Flow Index (15m to daily) (`mfi`) | 4.05 / 3.74 | 1.77 / 1.29 | - | 3.24 / 2.04 |
| Volume profile (session and 7 days) (`vprofile`) | 4.51 / 3.68 | 1.72 / 1.27 | - | 2.95 / 1.38 |
| Heikin-Ashi trend (15m to 4h) (`heikin`) | 4.00 / 4.01 | 4.19 / 2.92 | 5.13 / 3.52 | 6.07 / 2.96 |
| Aroon and Vortex (1h to daily) (`aroon`) | 6.68 / 6.38 | 4.93 / 3.17 | 6.16 / 4.44 | 8.46 / 3.22 |
| CCI (15m to daily) (`cci`) | 3.96 / 3.36 | 2.78 / 2.10 | 3.44 / 2.93 | 4.78 / 1.60 |
| Options flow (Deribit) (`optflow`) | 2.77 / 1.10 | - | - | - |
| Korea premium (`kprem`) | 1.57 / 1.60 | - | - | - |
| CME gap (spot proxy) (`cmegap`) | 1.65 / 1.17 | - | - | - |
| BTC dominance (`dom`) | 1.91 / 1.27 | - | - | - |
| Spot vs perp leadership (`spotlead`) | 1.98 / 1.84 | - | - | - |
| Cross-exchange funding and OI (`xfund`) | 3.17 / 1.24 | - | - | - |
| Daily range budget and range breaks (`adr`) | 5.01 / 5.15 | 3.16 / 1.83 | 3.53 / 2.52 | 3.53 / 2.21 |
| Williams %R (15m to daily) (`willr`) | 3.85 / 3.70 | 2.29 / 1.77 | 3.16 / 2.91 | 4.83 / 1.42 |
| Chaikin money flow and OBV (1h to daily) (`cmf`) | 4.15 / 2.73 | 3.25 / 3.11 | - | 4.53 / 2.66 |
| Elder-Ray (1h to daily) (`elder`) | 4.92 / 4.23 | 3.44 / 3.01 | 4.25 / 5.63 | 8.54 / 2.97 |
| Pivot points (daily and weekly) (`pivots`) | 4.75 / 4.22 | 3.06 / 2.56 | 3.42 / 2.72 | 4.82 / 2.31 |
| RSI divergence (15m to 4h) (`rsidiv`) | 2.16 / 1.52 | 3.19 / 3.07 | 2.06 / 1.62 | 2.70 / 3.87 |
| Fisher Transform (15m to 4h) (`fisher`) | 3.59 / 3.24 | 2.45 / 1.78 | 4.37 / 3.55 | 5.14 / 3.42 |
| Ultimate Oscillator (15m, 1h, daily) (`ultosc`) | 2.66 / 2.35 | 1.81 / 2.66 | 2.40 / 2.65 | 3.05 / 1.38 |
| TRIX (1h to daily) (`trix`) | 5.62 / 3.69 | 4.21 / 2.62 | 4.86 / 3.00 | 8.01 / 3.56 |
| Linear-regression channel (1h to daily) (`linreg`) | 5.68 / 4.99 | 4.17 / 3.69 | 4.66 / 3.10 | 6.46 / 4.43 |
| Mass Index (1h to daily) (`mass`) | 2.28 / 1.64 | 2.01 / 0.71 | 1.38 / 1.74 | 3.98 / 1.97 |

