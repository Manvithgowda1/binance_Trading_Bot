"""
validators.py — Input validation logic for order parameters.
Raises ValueError with a clear message on any invalid input.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol or raise ValueError."""
    s = symbol.strip().upper()
    # Allow alphanumeric: covers pairs like BTCUSDT, ETHUSDT, 1000PEPEUSDT
    if not s or not s.isalnum():
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphanumeric, e.g. BTCUSDT."
        )
    return s


def validate_side(side: str) -> str:
    """Return uppercased side or raise ValueError."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return s


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise ValueError."""
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate quantity; must be positive."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str | float]) -> Optional[Decimal]:
    """Parse and validate price when provided; must be positive."""
    if price is None:
        return None
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_stop_price(stop_price: Optional[str | float]) -> Optional[Decimal]:
    """Parse and validate stop price when provided; must be positive."""
    if stop_price is None:
        return None
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stop price '{stop_price}'. Must be a positive number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")
    return sp


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Validate all order parameters and enforce cross-field rules:
      - LIMIT orders require --price.
      - STOP_MARKET orders require --stop-price.
      - MARKET orders must not have --price.

    Returns a dict of cleaned, validated values.
    """
    cleaned = {
        "symbol":     validate_symbol(symbol),
        "side":       validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity":   validate_quantity(quantity),
        "price":      validate_price(price),
        "stop_price": validate_stop_price(stop_price),
    }

    ot = cleaned["order_type"]

    if ot == "LIMIT" and cleaned["price"] is None:
        raise ValueError("A price is required for LIMIT orders (use --price).")

    if ot == "STOP_MARKET" and cleaned["stop_price"] is None:
        raise ValueError("A stop price is required for STOP_MARKET orders (use --stop-price).")

    if ot == "MARKET" and cleaned["price"] is not None:
        raise ValueError("Do not supply --price for MARKET orders.")

    return cleaned
