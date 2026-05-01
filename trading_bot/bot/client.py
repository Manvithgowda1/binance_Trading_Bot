"""
client.py — Low-level Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Server-time synchronisation (timestamp offset)
  - HTTP request dispatch with structured logging
  - Binance API error unwrapping
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response or an error payload."""

    def __init__(self, code: int, message: str, status_code: int = 0):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"Binance API error {code}: {message}")


class BinanceFuturesClient:
    """
    Thin wrapper around Binance USDT-M Futures Testnet REST API.

    Responsibilities
    ────────────────
    • Sign private requests with HMAC-SHA256.
    • Keep a timestamp offset to avoid 'timestamp out of range' errors.
    • Log every outbound request and inbound response at DEBUG level.
    • Raise BinanceAPIError on API-level failures.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = TESTNET_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        self._time_offset: int = 0
        self._sync_time()

    # ── Time synchronisation ──────────────────────────────────────────────────

    def _sync_time(self) -> None:
        """Compute clock offset against Binance server time."""
        try:
            local_before = int(time.time() * 1000)
            resp = self._session.get(f"{self._base_url}/fapi/v1/time", timeout=10)
            local_after = int(time.time() * 1000)
            resp.raise_for_status()
            server_time = resp.json()["serverTime"]
            self._time_offset = server_time - ((local_before + local_after) // 2)
            logger.debug("Time offset synced: %+d ms", self._time_offset)
        except Exception as exc:
            logger.warning("Time sync failed (%s). Using local time.", exc)
            self._time_offset = 0

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset

    # ── Request signing ───────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ── Core HTTP helpers ─────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Any:
        url = f"{self._base_url}{path}"
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = RECV_WINDOW
            params["signature"] = self._sign(params)

        # Redact signature before logging
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("→ %s %s  params=%s", method.upper(), path, log_params)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(method, url, params=params, timeout=15)
            else:
                response = self._session.request(method, url, data=params, timeout=15)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection failed: %s", exc)
            raise
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise

        logger.debug(
            "← %s %s  status=%s  body=%s",
            method.upper(),
            path,
            response.status_code,
            response.text[:500],
        )

        # Binance signals errors with a negative 'code' in the JSON body,
        # even on HTTP 200. Only treat it as an error when code < 0.
        if not response.ok:
            try:
                payload = response.json()
                code = payload.get("code", response.status_code)
                msg = payload.get("msg", response.text)
            except Exception:
                code = response.status_code
                msg = response.text
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg, response.status_code)

        try:
            payload = response.json()
        except Exception:
            return response.text

        # Negative code in a 2xx response means Binance-level error
        if isinstance(payload, dict) and payload.get("code", 0) < 0:
            code = payload["code"]
            msg = payload.get("msg", "Unknown error")
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg, response.status_code)

        return payload

    # ── Public API methods ────────────────────────────────────────────────────

    def get_server_time(self) -> Dict:
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self) -> Dict:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **order_params) -> Dict:
        """
        Place a futures order.  All keyword args are forwarded as POST params.
        Returns the raw Binance order response dict.
        """
        return self._request("POST", "/fapi/v1/order", params=order_params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> Any:
        params: Dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
