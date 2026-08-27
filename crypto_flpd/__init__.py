"""Realistic, data-honest reconstruction of the three FLPD-paper building
blocks (ssrn-6880798, "Multifractal Price Delivery in Algorithmic Futures
Markets") on top of this repo's actual crypto data (Binance klines via
auction_playbook.data.fetch_klines - OHLCV + taker buy/sell volume +
n_trades, no order-book depth). See resources/crypto-hurst-wyckoff-cycles.md
for the paper distillation and the reasoning behind every proxy/simplification
made here, and knowledge/projects (plan) for the full design rationale.

- hurst.py: Baustein 1, dynamic Hurst exponent (DFA-2) + collapse detection.
- liquidity.py: Baustein 2, Temporal-Liquidity-Vacuum PROXY (no order book).
- phases.py: Baustein 3, Psi multiscale delivery matrix (rule-based phases,
  not the paper's Baum-Welch HMM).
- engine.py: trading simulations (Phase A: Hurst-exit overlay on the
  existing btc_ema_cross baseline; Phase B: full Psi-threshold strategy).
- significance.py: re-simulation-based randomization test for signal timing
  (reuses asian_range_breakout.randomization's shuffle primitives)."""
