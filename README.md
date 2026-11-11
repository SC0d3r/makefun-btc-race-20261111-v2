# btc-race-24h-entry-v2

A long-only Python bot for make.fun's `agent-fun/bars-replay/v1` replay of
CBBTC/USDC one-minute bars.

## Strategy

A full round trip costs roughly 19-26 bps in fees, modelled slippage and
constant-product price impact, so the bot buys a dip only when the bounce has
already started. On each bar's close it buys with all its cash when:

- the close is at least 25 bps below the 70-bar simple moving average, and
- the close is above its level 8 bars ago (a short-term turn, not a falling
  knife).

It exits at +50 bps over its cost, at a -150 bps stop (tail insurance; it never
triggers on the dev window), or after 360 bars. A one-USDC minimum-notional
round trip on the first two batches guarantees at least one filled trade on any
window.

The bot is deterministic: no clock, no network, no randomness, integer
arithmetic only.

## Layout

- `main.py` - entrypoint and strategy
- `vendor/makefun_bars.py` - byte-identical copy of the kit's Python SDK shim
- `LICENSE` - MIT

## Run

The grader runs:

```
python3 -P -s /bot/main.py
```

Locally, from the unpacked kit:

```
node cli/makefun.mjs grade-local --kit . --bot /path/to/btc-race-24h-entry-v2 --driver docker --json
```

Dev-window grade: net PnL +22.510174 USDC, 12 trades, 0.999% max drawdown,
`l1.reproduced` true.
