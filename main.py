import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# Dense long-only mean-reversion bot for the make.fun CBBTC 24h bars replay.
#
# One symbol, one position, long only. A round trip costs roughly 19-26 bps in
# fees, modelled slippage and constant-product price impact, so the bot buys
# only when the close is far enough below a slow moving average to pay for the
# round trip, and takes a fixed profit or exits on a time limit.
#
# The first two batches send a one-USDC minimum-notional round trip so the
# race window always has at least one filled trade even if the strategy never
# fires. All arithmetic is integer, so the bot is deterministic.

SYMBOL = "CBBTC"
BPS = 10000
MIN_NOTIONAL = 1_000_000  # 1 USDC in quote units

# Entry: close at least X bps below the SMA of the last N closes, and the
# close above its level TURN_K bars ago (a short-term turn, not a falling knife).
N_BARS = 70
X_BPS = 25
TURN_K = 8

# Exit: +TAKE bps over cost, a -STOP bps stop as tail insurance, or MAX_HOLD
# bars, whichever comes first.
TAKE_BPS = 50
STOP_BPS = 150
MAX_HOLD_BARS = 360

# Spend all cash on one entry.
SIZE_PCT = 100
MAX_SLIPPAGE_BPS = 10000

_closes = []
_sum = 0
_entry_seq = -1
# The one-USDC probe: 0 = still to buy, 1 = bought and still to sell, 2 = done.
_compliance = 0


def _buy(state, notional):
    notional = min(notional, state.cash, state.weight_room(SYMBOL))
    if notional < MIN_NOTIONAL:
        return None
    return {
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": notional,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def _sell(held):
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": held.qty,
        "max_slippage_bps": MAX_SLIPPAGE_BPS,
    }


def on_batch(state, batch):
    global _sum, _entry_seq, _compliance

    bar = None
    for b in batch["bars"]:
        if b["symbol"] == SYMBOL:
            bar = b
    if bar is not None:
        _closes.append(int(bar["c"]))
        _sum += int(bar["c"])
        if len(_closes) > N_BARS:
            _sum -= _closes[-1 - N_BARS]

    seq = batch["seq"]
    held = state.positions.get(SYMBOL)

    # The one-USDC probe: buy it on the first batch that has a bar, sell it as
    # soon as it fills, and retry either leg if the market refuses it.
    if _compliance < 2:
        if _compliance == 0:
            if held is not None:
                _compliance = 1
            elif bar is not None:
                order = _buy(state, MIN_NOTIONAL)
                return [order] if order is not None else []
            else:
                return []
        if _compliance == 1:
            if held is None:
                _compliance = 2
            else:
                return [_sell(held)]

    if held is not None:
        if _entry_seq < 0:
            _entry_seq = seq
        value = state.value(SYMBOL, held.qty)
        take = value * BPS >= held.cost * (BPS + TAKE_BPS)
        stop = value * BPS <= held.cost * (BPS - STOP_BPS)
        old = seq - _entry_seq >= MAX_HOLD_BARS
        if take or stop or old:
            return [_sell(held)]
        return []

    _entry_seq = -1
    if len(_closes) >= N_BARS and len(_closes) > TURN_K:
        # close * BPS * N <= sum * (BPS - X): close is X bps under the SMA,
        # and close > close TURN_K bars ago: the dip is already turning up.
        if (_closes[-1] * BPS * N_BARS <= _sum * (BPS - X_BPS)
                and _closes[-1] > _closes[-1 - TURN_K]):
            notional = state.cash * SIZE_PCT // 100
            order = _buy(state, notional)
            return [order] if order is not None else []
    return []


def main():
    makefun_bars.run(on_batch)


if __name__ == "__main__":
    main()
