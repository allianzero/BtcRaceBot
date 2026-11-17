# BUILD_LOG — BtcRaceBot (Dip Rider)

Competition: btc-race-24h-20261117-0603 — "Race a BTC trading bot live for
24 hours". Prize $250 USDC, free entry. Built 2026-11-17, deadline
19:03 WIB the same day.

## Strategy

Dip Rider (original): buy the dip, then ride it.

- Entry: close within 10 bps of the lowest low of the last 240 bars AND
  close above its close 5 bars back. One buy, 100% of cash.
- Exit: trailing stop 300 bps below the highest close since entry. No
  take-profit, no reversal exit.
- Fallback: if still flat by bar 1080 and the trailing 30-bar return is
  above +30 bps, buy once (guarantees >= 1 trade on any window).
- Cooldown: 60 bars with no entries after a stop-out sell.
- No entries after bar 1380. Max slippage 100 bps per order.

Parameters (few, round, chosen for robustness, not a knife-edge):
LOW_LOOKBACK=240, NEAR_LOW_BPS=10, RECOVERY_BARS=5, TRAIL_BPS=300,
FALLBACK_BAR=1080, FALLBACK_LOOKBACK=30, LAST_ENTRY_BAR=1380,
MAX_SLIPPAGE_BPS=100, size 100% of cash.

## Why this shape

Dev window analysis (1,440 bars, BTC +48 bps over 24h, per-minute return
stdev 6.4 bps): a full-size round trip costs ~26-38 bps in fees (4 bps),
slippage (2 bps) and pool impact, so frequent trading loses to costs.
Kit baselines on the dev window (grade-local, process driver):
buy-and-hold +$1.07 (1 trade), momentum +$2.45 (1 trade),
ema-cross -$106.21 (68 trades, 8.8% win rate), rsi-bollinger -$24.25,
adx-momentum -$32.66. Every EMA-cross / rider / Donchian grid I backtested
lost money; only buy-once-and-hold won. Dip Rider buys the window's low
region (bar ~375, $63,944) and holds to the end.

Robustness checks (offline backtester, same fill model):
- Full window: +$9.32, 1 trade, max DD 2.12%.
- Plateau, not a peak: trail 250/300/400 all +$9.32; eps 5/10/20 all
  +$9.32; n_low 120/240/360 all +$9.32.
- First half (0-720): +$8.93. Second half (720-1440): -$2.20 (buys a
  late dip that does not recover before the window ends) — the known
  worst case is a few dollars, far inside the 25% drawdown guardrail.

## Verification of the actual bot

`grade-local --driver process` on this machine runs Node only, and Docker
is not installed, so the official grader cannot run this Python bot here.
Instead the shipped main.py was run end-to-end twice through a local replay
driver (/tmp/replay.py) that implements the harness's exact integer fill
formulas (buy: spend = notional less 4 bps fee, fill price = open x
(1 + 2 bps slippage) x (1 + spend/depth); sell symmetric; fills at the
next bar's open; final flatten at the last close) over the kit's dev bars:

- Run 1: net PnL +9.322902 USDC, 1 trade, max drawdown 2.12%.
- Run 2: net PnL +9.322902 USDC, 1 trade, max drawdown 2.12%.
- Deterministic: byte-identical action logs across both runs.
- Protocol: exactly one reply per batch, each echoing its seq; clean exit,
  no stderr output.

The offline backtester agreed (+$9.32), and the same driver reproduces
the kit baselines (buy-and-hold +$1.0673 vs official +$1.067187;
momentum +$2.4460 vs +$2.445627), so the fill model is faithful.

TODO for the lead: run the official `grade-local --kit . --bot
~/workspace/makefun/BtcRaceBot --driver docker` (or the server grade) to
confirm, then push + submit before 19:03 WIB. Do NOT edit README.md after
the recording seals.

## Files

- main.py (entrypoint, Python 3.13, stdlib only)
- vendor/makefun_bars.py (byte-identical copy of the kit SDK shim)
- README.md, LICENSE (MIT, SPDX line), .makefun/owner.json
