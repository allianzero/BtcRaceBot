# BtcRaceBot — Dip Rider

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/allianzero/BtcRaceBot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/allianzero/BtcRaceBot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

A long-only cbBTC/USDC trading bot for the make.fun competition
**btc-race-24h-20261117-0603** ("Race a BTC trading bot live for 24
hours"). It trades 1-minute on-chain bars of Coinbase Wrapped BTC against
USDC with $1,000 of paper money, speaking the `agent-fun/bars-replay/v1`
protocol: one `hello`, one `batch` per minute bar, one `reply` per batch
echoing its `seq`.

## Strategy — buy the dip, then ride it

On the dev window BTC drifts almost flat (+48 bps over 24h) while a
full-size round trip costs ~26–38 bps in fees, slippage and pool impact,
so frequent trading loses to costs — the kit's EMA-cross baseline makes 68
trades and loses $106. The money is in one well-timed entry at a local
low, held through the grind.

- **Entry (flat only):** the bar's close sits within 10 bps of the lowest
  low of the last 240 bars **and** the close has turned up over the last
  5 bars. One buy, 100% of cash.
- **Exit (holding only):** a trailing stop 300 bps below the highest close
  seen since entry. No take-profit, no reversal exit — a real trend is
  ridden to the end of the window.
- **Fallback entry:** if still flat by bar 1080 and the trailing 30-bar
  return is above +30 bps, buy once, so the bot always takes at least one
  trade on any window.
- **Cooldown:** after a stop-out sell, no new entry for 60 bars, so a
  stopped-out dip is not bought straight back into a falling market.
- **No entries after bar 1380** (an order on the last batch is rejected
  anyway, and a fill that late only pays costs).

Every decision is pure integer arithmetic on the closes and lows the
batches carried. No randomness, no wall clock, no network, no files
outside the repository — two runs on the same bars give the same orders,
byte for byte.

## Parameters

| Parameter | Value |
|---|---|
| Low lookback | 240 bars |
| Near-low band | 10 bps |
| Recovery lookback | 5 bars |
| Trailing stop | 300 bps |
| Fallback bar / return | 1080 / +30 bps over 30 bars |
| Position size | 100% of cash |
| Max slippage | 100 bps |

## Dev window result (local verification)

- **Net PnL: +9.322902 USDC** (gate: > 0)
- Trades: 1 · Max drawdown: 2.12% (guardrail: ≤ 25%)
- Deterministic: two independent runs produced byte-identical action logs.

Verification used a local replay driver that implements the harness's exact
integer fill formulas (fee 4 bps, slippage 2 bps, constant-product impact
against the fill bar's open depth, fills at the next bar's open), because
`grade-local --driver process` on this machine runs Node only and Docker is
unavailable for the Python runtime. See `BUILD_LOG.md`.

## Layout

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — byte-identical copy of the kit's Python shim
- `.makefun/owner.json` — claim file for the entry wallet
- `BUILD_LOG.md` — strategy notes and verification results

## License

MIT — see `LICENSE`.
