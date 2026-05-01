#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet Trading Bot.

Usage examples (see README.md for full list):
  python cli.py place --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.001
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.001 --price 80000
  python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000
  python cli.py account
  python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import OrderManager, OrderResult
from bot.validators import validate_order_params

# ── Logger ────────────────────────────────────────────────────────────────────
setup_logging()
logger = get_logger("cli")

# ── ANSI colours (degraded gracefully on Windows) ─────────────────────────────
_USE_COLOR = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

GREEN   = lambda t: _c(t, "32")
RED     = lambda t: _c(t, "31")
YELLOW  = lambda t: _c(t, "33")
CYAN    = lambda t: _c(t, "36")
BOLD    = lambda t: _c(t, "1")
DIM     = lambda t: _c(t, "2")


# ── Output helpers ─────────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_order_request(params: dict) -> None:
    print()
    print(BOLD(_divider("═")))
    print(BOLD("  ORDER REQUEST SUMMARY"))
    print(_divider())
    fields = [
        ("Symbol",     params["symbol"]),
        ("Side",       params["side"]),
        ("Type",       params["order_type"]),
        ("Quantity",   str(params["quantity"])),
    ]
    if params.get("price"):
        fields.append(("Price", str(params["price"])))
    if params.get("stop_price"):
        fields.append(("Stop Price", str(params["stop_price"])))
    for label, value in fields:
        print(f"  {DIM(label+':'):<22}{CYAN(value)}")
    print(_divider())


def _print_order_result(result: OrderResult) -> None:
    if result.success:
        print(GREEN("  ✓ ORDER PLACED SUCCESSFULLY"))
        print(_divider())
        rows = [
            ("Order ID",       str(result.order_id)),
            ("Client Order ID", result.client_order_id or "—"),
            ("Status",         result.status or "—"),
            ("Executed Qty",   result.executed_qty or "—"),
            ("Avg Price",      result.avg_price or "—"),
            ("Orig Qty",       result.orig_qty or "—"),
            ("Price",          result.price or "MARKET"),
        ]
        for label, value in rows:
            print(f"  {DIM(label+':'):<22}{value}")
    else:
        print(RED("  ✗ ORDER FAILED"))
        print(_divider())
        print(f"  {DIM('Error:')}  {RED(result.error or 'Unknown error')}")
    print(BOLD(_divider("═")))
    print()


# ── Credential loading ─────────────────────────────────────────────────────────

def _load_credentials() -> tuple[str, str]:
    """
    Load API credentials from environment variables:
      BINANCE_API_KEY
      BINANCE_API_SECRET
    """
    api_key    = os.environ.get("BINANCE_API_KEY", "").strip()
    api_secret = os.environ.get("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print(RED("Error: BINANCE_API_KEY and BINANCE_API_SECRET must be set."))
        print(DIM("  export BINANCE_API_KEY=your_key"))
        print(DIM("  export BINANCE_API_SECRET=your_secret"))
        sys.exit(1)
    return api_key, api_secret


# ── Sub-command handlers ───────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace) -> int:
    """Validate input, build client, place order, print result."""
    # ── Validate ──────────────────────────────────────────────────────────────
    try:
        params = validate_order_params(
            symbol     = args.symbol,
            side       = args.side,
            order_type = args.type,
            quantity   = args.quantity,
            price      = args.price,
            stop_price = args.stop_price,
        )
    except ValueError as exc:
        logger.error("Validation failed: %s", exc)
        print(RED(f"\n  Validation Error: {exc}\n"))
        return 1

    _print_order_request(params)

    # ── Connect ───────────────────────────────────────────────────────────────
    api_key, api_secret = _load_credentials()
    try:
        client  = BinanceFuturesClient(api_key, api_secret)
        manager = OrderManager(client)
    except Exception as exc:
        logger.error("Failed to initialise client: %s", exc)
        print(RED(f"  Client error: {exc}"))
        return 1

    # ── Dispatch ──────────────────────────────────────────────────────────────
    ot = params["order_type"]
    if ot == "MARKET":
        result = manager.place_market_order(
            symbol   = params["symbol"],
            side     = params["side"],
            quantity = params["quantity"],
        )
    elif ot == "LIMIT":
        result = manager.place_limit_order(
            symbol   = params["symbol"],
            side     = params["side"],
            quantity = params["quantity"],
            price    = params["price"],
            time_in_force = args.tif or "GTC",
        )
    elif ot == "STOP_MARKET":
        result = manager.place_stop_market_order(
            symbol     = params["symbol"],
            side       = params["side"],
            quantity   = params["quantity"],
            stop_price = params["stop_price"],
        )
    else:
        print(RED(f"  Unsupported order type: {ot}"))
        return 1

    _print_order_result(result)
    return 0 if result.success else 1


def cmd_account(args: argparse.Namespace) -> int:
    """Fetch and display account balance summary."""
    api_key, api_secret = _load_credentials()
    try:
        client = BinanceFuturesClient(api_key, api_secret)
        data   = client.get_account()
    except BinanceAPIError as exc:
        print(RED(f"  API Error: {exc}"))
        return 1
    except Exception as exc:
        logger.exception("Account fetch failed: %s", exc)
        print(RED(f"  Error: {exc}"))
        return 1

    print()
    print(BOLD(_divider("═")))
    print(BOLD("  ACCOUNT SUMMARY"))
    print(_divider())
    print(f"  {DIM('Total Wallet Balance:'):<30}{data.get('totalWalletBalance','—')} USDT")
    print(f"  {DIM('Available Balance:'):<30}{data.get('availableBalance','—')} USDT")
    print(f"  {DIM('Unrealised PnL:'):<30}{data.get('totalUnrealizedProfit','—')} USDT")
    print(f"  {DIM('Margin Balance:'):<30}{data.get('totalMarginBalance','—')} USDT")
    print(BOLD(_divider("═")))
    print()
    return 0


def cmd_open_orders(args: argparse.Namespace) -> int:
    """List open orders, optionally filtered by symbol."""
    api_key, api_secret = _load_credentials()
    try:
        client = BinanceFuturesClient(api_key, api_secret)
        orders = client.get_open_orders(symbol=args.symbol)
    except BinanceAPIError as exc:
        print(RED(f"  API Error: {exc}"))
        return 1
    except Exception as exc:
        logger.exception("Open orders fetch failed: %s", exc)
        print(RED(f"  Error: {exc}"))
        return 1

    print()
    print(BOLD(_divider("═")))
    header = f"  OPEN ORDERS{f'  ({args.symbol})' if args.symbol else ''}"
    print(BOLD(header))
    print(_divider())
    if not orders:
        print(DIM("  No open orders."))
    else:
        for o in orders:
            print(
                f"  [{o.get('orderId')}]  "
                f"{o.get('symbol')}  "
                f"{CYAN(o.get('side'))}  "
                f"{o.get('type')}  "
                f"qty={o.get('origQty')}  "
                f"price={o.get('price')}  "
                f"status={YELLOW(o.get('status'))}"
            )
    print(BOLD(_divider("═")))
    print()
    return 0


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Market BUY
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 80000

  # Stop-Market (bonus)
  python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 75000

  # Account info
  python cli.py account

  # Open orders for ETHUSDT
  python cli.py open-orders --symbol ETHUSDT
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── place ─────────────────────────────────────────────────────────────────
    place = sub.add_parser("place", help="Place a new order")
    place.add_argument("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
    place.add_argument("--side",       required=True,  choices=["BUY", "SELL"],
                       type=str.upper, help="BUY or SELL")
    place.add_argument("--type",       required=True,
                       choices=["MARKET", "LIMIT", "STOP_MARKET"],
                       type=str.upper, dest="type", help="Order type")
    place.add_argument("--quantity",   required=True,  type=float,
                       help="Order quantity in base asset")
    place.add_argument("--price",      required=False, type=float, default=None,
                       help="Limit price (required for LIMIT orders)")
    place.add_argument("--stop-price", required=False, type=float, default=None,
                       dest="stop_price",
                       help="Stop trigger price (required for STOP_MARKET orders)")
    place.add_argument("--tif",        required=False, default="GTC",
                       choices=["GTC", "IOC", "FOK"],
                       help="Time-in-force for LIMIT orders (default: GTC)")
    place.set_defaults(func=cmd_place)

    # ── account ───────────────────────────────────────────────────────────────
    acct = sub.add_parser("account", help="Show account balance summary")
    acct.set_defaults(func=cmd_account)

    # ── open-orders ───────────────────────────────────────────────────────────
    oo = sub.add_parser("open-orders", help="List open orders")
    oo.add_argument("--symbol", required=False, default=None,
                    help="Filter by symbol, e.g. BTCUSDT")
    oo.set_defaults(func=cmd_open_orders)

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    try:
        exit_code = args.func(args)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
