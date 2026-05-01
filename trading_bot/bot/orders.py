"""
orders.py — High-level order placement logic.

Sits between the raw BinanceFuturesClient and the CLI layer.
Responsible for:
  - Building the correct parameter set per order type
  - Logging a human-readable order summary before/after placement
  - Returning a structured OrderResult dataclass
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceAPIError
from .logging_config import get_logger

logger = get_logger("orders")


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    orig_qty: Optional[str] = None
    price: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class OrderManager:
    """
    Provides place_market_order(), place_limit_order(), and
    place_stop_market_order(). All methods log a summary before and after
    placement and return an OrderResult.
    """

    def __init__(self, client: BinanceFuturesClient):
        self._client = client

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _parse_response(self, raw: dict) -> OrderResult:
        return OrderResult(
            success=True,
            order_id=raw.get("orderId"),
            client_order_id=raw.get("clientOrderId"),
            symbol=raw.get("symbol"),
            side=raw.get("side"),
            order_type=raw.get("type"),
            status=raw.get("status"),
            executed_qty=raw.get("executedQty"),
            avg_price=raw.get("avgPrice"),
            orig_qty=raw.get("origQty"),
            price=raw.get("price"),
            raw=raw,
        )

    def _place(self, label: str, params: dict) -> OrderResult:
        """Shared dispatch: log → place → parse, with unified error handling."""
        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            params.get("side"),
            params.get("type"),
            params.get("symbol"),
            params.get("quantity"),
            params.get("price") or params.get("stopPrice") or "MARKET",
        )
        try:
            raw = self._client.place_order(**params)
            result = self._parse_response(raw)
            logger.info(
                "%s order placed ✓ | orderId=%s status=%s executedQty=%s avgPrice=%s",
                label,
                result.order_id,
                result.status,
                result.executed_qty,
                result.avg_price,
            )
            return result
        except BinanceAPIError as exc:
            logger.error("%s order failed — %s", label, exc)
            return OrderResult(success=False, error=str(exc))
        except Exception as exc:
            logger.exception("Unexpected error placing %s order: %s", label, exc)
            return OrderResult(success=False, error=str(exc))

    # ── Public API ────────────────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
    ) -> OrderResult:
        return self._place("Market", {
            "symbol":   symbol,
            "side":     side,
            "type":     "MARKET",
            "quantity": str(quantity),
        })

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        return self._place("Limit", {
            "symbol":      symbol,
            "side":        side,
            "type":        "LIMIT",
            "quantity":    str(quantity),
            "price":       str(price),
            "timeInForce": time_in_force,
        })

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        stop_price: Decimal,
    ) -> OrderResult:
        """Bonus order type — triggers a market order when price hits stop_price."""
        return self._place("Stop-Market", {
            "symbol":    symbol,
            "side":      side,
            "type":      "STOP_MARKET",
            "quantity":  str(quantity),
            "stopPrice": str(stop_price),
        })
