"""BtcRaceBot -- Dip Rider for make.fun btc-race-24h-20261117-0603.

A long-only cbBTC/USDC bot that speaks agent-fun/bars-replay/v1 over
newline-delimited JSON: it reads one hello, then one batch per minute bar,
and answers every batch with exactly one reply echoing its seq and carrying
its orders (at most one order per batch here).

Strategy -- buy the dip, then ride it:
  * Entry (flat only): the bar's close sits within NEAR_LOW_BPS of the
    lowest low of the last LOW_LOOKBACK bars AND the close has turned up
    over the last RECOVERY_BARS bars. One buy, 100% of cash.
  * Exit (holding only): a trailing stop TRAIL_BPS below the highest close
    seen since entry. Nothing else sells: no take-profit, no reversal exit,
    so a real trend is ridden to the end of the window.
  * Fallback entry: if still flat by FALLBACK_BAR and the trailing
    FALLBACK_LOOKBACK-bar return is above +30 bps, buy once, so the bot
    always takes at least one trade on any window -- but only on a
    genuinely positive trend, never on a weak blip in a downtrend.
  * No new entries after LAST_ENTRY_BAR (an order on the last batch would
    be rejected anyway, and a fill that late only pays costs).

Why this shape: on the dev window BTC drifts almost flat (+48 bps over
24h) while a full-size round trip costs ~26-38 bps in fees, slippage and
pool impact, so frequent trading loses to costs (the kit's EMA-cross
baseline makes 68 trades and loses $106). The money is in one well-timed
entry at a local low, held through the grind. The wide trailing stop is
the only defence: it caps a falling-knife loss near 3% while letting a
rally run.

Determinism: every decision is pure integer arithmetic on the closes and
lows the batches carried. No randomness, no wall clock, no network, no
files outside the repository. Two runs on the same bars give the same
orders, byte for byte.
"""

import os
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
)
import makefun_bars

SYMBOL = "CBBTC"

# --- strategy parameters (few, round, chosen on the dev window) ---
LOW_LOOKBACK = 240      # bars of low history for the dip test
NEAR_LOW_BPS = 10       # close within this many bps of the lookback low
RECOVERY_BARS = 5       # close must be above its close this many bars back
TRAIL_BPS = 300         # trailing stop, bps below the peak close since entry
FALLBACK_BAR = 1080     # if still flat by this bar, take the fallback entry
FALLBACK_LOOKBACK = 30  # fallback buys on a positive return over this many bars
LAST_ENTRY_BAR = 1380   # never open a new position after this bar
MAX_SLIPPAGE_BPS = 100  # 1% past the close the order was decided on


class DipRider:
    """The strategy state: the closes and lows each batch carried, and the
    highest close seen while holding (the trailing stop's peak)."""

    def __init__(self):
        self.closes = []   # int closes, oldest first, one per CBBTC bar
        self.lows = []     # int lows, same order
        self.peak = 0      # highest close since the current entry
        # No entries before this bar count: set 60 bars past a stop-out
        # sell, so a stopped-out dip is not bought straight back into a
        # falling market.
        self.cooldown_until = 0

    def note_bar(self, close, low):
        self.closes.append(close)
        self.lows.append(low)

    def near_low(self):
        """True when the latest close is within NEAR_LOW_BPS of the lowest
        low of the last LOW_LOOKBACK bars."""
        if len(self.closes) < LOW_LOOKBACK:
            return False
        low = min(self.lows[-LOW_LOOKBACK:])
        close = self.closes[-1]
        return (close - low) * 10_000 <= NEAR_LOW_BPS * low

    def recovering(self):
        """True when the latest close is above its close RECOVERY_BARS back."""
        if len(self.closes) <= RECOVERY_BARS:
            return False
        return self.closes[-1] > self.closes[-1 - RECOVERY_BARS]

    def trailing_return_bps(self, lookback):
        """The return in bps over the last `lookback` bars, or None."""
        if len(self.closes) <= lookback:
            return None
        then = self.closes[-1 - lookback]
        now = self.closes[-1]
        return (now - then) * 10_000 // then

RIDER = DipRider()


def on_batch(state, batch):
    """Decide the orders for one batch. Returns a list of order dicts
    (possibly empty); the shim turns them into the reply for this batch."""
    bar = None
    for candidate in batch["bars"]:
        if candidate["symbol"] == SYMBOL:
            bar = candidate
            break
    if bar is None:
        # No CBBTC bar this minute: nothing to decide on.
        return []
    RIDER.note_bar(int(bar["c"]), int(bar["l"]))
    if state.warming_up:
        # Warm-up batches build history only; orders here are rejected.
        return []

    holding = state.positions.get(SYMBOL)
    qty = holding.qty if holding is not None else 0
    close = RIDER.closes[-1]
    n_bars = len(RIDER.closes)

    if qty > 0:
        # Holding: track the peak and sell everything on the trailing stop.
        if close > RIDER.peak:
            RIDER.peak = close
        if (RIDER.peak - close) * 10_000 >= TRAIL_BPS * RIDER.peak:
            RIDER.cooldown_until = n_bars + 60
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    # Flat: look for an entry, never after the last entry bar, never
    # inside the cooldown after a stop-out sell.
    if n_bars > LAST_ENTRY_BAR:
        return []
    if n_bars < RIDER.cooldown_until:
        return []
    if state.cash < int(state.hello["fees"]["min_notional_quote_units"]):
        return []

    dip = RIDER.near_low() and RIDER.recovering()
    fallback = False
    if not dip and n_bars >= FALLBACK_BAR:
        ret = RIDER.trailing_return_bps(FALLBACK_LOOKBACK)
        fallback = ret is not None and ret > 30
    if dip or fallback:
        RIDER.peak = close
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": state.cash,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]
    return []


def on_hello(state):
    """The hello carries the universe, capital, caps and seed; nothing to
    seed here -- the bot is fully deterministic without randomness."""
    return None


makefun_bars.run(on_batch, on_hello=on_hello)
