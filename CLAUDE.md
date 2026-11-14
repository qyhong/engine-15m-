# Mind 15: context for a Claude session in this folder

This folder is a stand-alone 15-minute paper-trading engine ("Mind 15") for eight markets in five
groups: crypto (BTCUSDT, ETHUSDT), metals (XAUUSD, XAGUSD), fx (USDJPY), index (SPX, cash hours) and
energy (WTI, BRENT). Each market has its own $10,000 paper book. Read, in order: `docs/CHARTER.md`
(the agreed purpose, every task and its status, decisions the owner has made), `THOUGHT_PROCESS.md`
(the design; its "Now" section lists what changed since it was first written), `HANDOFF.md` (moving parts).

Beside the main books run, all forward and on paper: shadow books (`engine15/shadows.py`: v4, H3, A, B,
H5, the 4h/daily yardsticks, the 1h/4h swing minds, the H36 exit shadows), twelve strategy books
(`engine15/playbook.py` to `playbook3.py`, H6-H17), the CPI book (H1), and forward books that are NOT passed:
rules A/B (`playbook4`), the RL agents (`playbook5`, `playbook6`) and the BTC/ETH pair book (`playbook7`, H37 V4).
Engine version think15-v5.1.1 (13 Nov 2026): four crypto reading-only cards from `engine15/sources/flows.py`.
`out/live/scoreboard.json` judges every book on live trades only.
Hypotheses are registered in `research/HYPOTHESES.md` before they are graded.

## Discussing the engine with the owner

The owner will ask what the engine is thinking and why. Answer from what the engine wrote,
never from your own view of the market:

- `journal/<YYYY-MM-DD>.jsonl`: one JSON line per coin per 15-minute close (live sessions).
  Fields: `decision` (a sentence), `action`, `position`, `odds`, `edge_pts`, `cards` (the ten
  cards: reading, pull, trust), `voices`, `for_long`, `for_short`, `data` (every reading),
  `graded_now`, `levels`, `econ_next`, `raw` (live feeds). `journal/<day>.md` is the same for reading.
- `journal/replay/`: days rendered from the history replay on request (`py -3 -m engine15 journal DATE`).
- `out/live/page.json`: the latest state as the web tab sees it.
- `py -3 -m engine15 ask now | why ETH | cards BTC | today | learning` prints ready answers.
- `py -3 -m engine15 postmortem [reading|trades] [--days N]` for look-backs.

Quote the readings and the reason the entry gives. If the journal does not hold the answer, say so.

## Rules

- Paper only. Nothing here places orders; do not add anything that does.
- Never describe a reading, a voice or Kronos as having a proven edge. The replay is a
  warm-up and post-mortem material, not validation (see THOUGHT_PROCESS.md).
- `C:\Ai Dataset\eth-signal-bot` (the AI Trading Bot) is read-only from here. Its own session owns it.
- Constants live in `engine15/config.py`. Changing one is a new version of the thought
  process: bump `version` and say so in the journal's next entry.
- Closed bars only; anything computed on 1h/4h/1d bars goes through `data.htf_on_15`.
  `tests/test_engine.py::test_evidence_never_reads_the_future` must stay green.
- The web tab on alphaprediction.ai/aitrading is deployed by the AI Trading Bot session's
  page pipeline (`C:\tmp\kronos\aitrading-pages`), on the owner's word. This project only writes `page.json`.
