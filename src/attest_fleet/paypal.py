"""PayPal sandbox REST client.

The agent ACTS through this module (refund a capture, cancel a subscription), and the
verifier READS PayPal's own record back through it — independently of whatever the agent
claimed. That independent read-back is the whole point of Refundly: "done" means PayPal
agrees, not that a tool returned 200.

Everything here is stdlib (urllib), so the client adds no dependency. Credentials come from
the environment via config; when none are set, config.PAYPAL_READY is False and every caller
falls back to the in-memory mock, so the app still runs for local dev and tests.

Currency is USD (the sandbox default). Amounts come from the demo orders, which are USD.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from . import config


class PayPalError(Exception):
    """A PayPal API call failed. Carries the status line so it lands in the evidence trail."""


_token: dict = {"value": None, "exp": 0.0}


def _access_token() -> str:
    now = time.time()
    if _token["value"] and _token["exp"] > now + 30:
        return _token["value"]
    if not config.PAYPAL_READY:
        raise PayPalError("PayPal is not configured (set PAYPAL_CLIENT_ID and PAYPAL_SECRET)")
    cred = base64.b64encode(f"{config.PAYPAL_CLIENT_ID}:{config.PAYPAL_SECRET}".encode()).decode()
    req = urllib.request.Request(
        config.PAYPAL_BASE + "/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        method="POST",
    )
    req.add_header("Authorization", f"Basic {cred}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:  # noqa: BLE001 — re-raised as PayPalError
        raise PayPalError(f"PayPal auth failed: {e.code} {e.read().decode()[:200]}") from e
    _token["value"] = d["access_token"]
    _token["exp"] = now + float(d.get("expires_in", 3000))
    return _token["value"]


def _api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        config.PAYPAL_BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
    )
    req.add_header("Authorization", f"Bearer {_access_token()}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise PayPalError(f"PayPal {method} {path} -> {e.code}: {e.read().decode()[:300]}") from e


# --------------------------------------------------------------- money actions (the agent)


def refund_capture(capture_id: str, amount: float | None = None, currency: str = "USD") -> dict:
    """Refund a captured payment (full refund when amount is None).

    Returns PayPal's refund resource. status == "COMPLETED" means the money actually moved;
    any other status (e.g. "PENDING") means it has NOT — which is exactly the silent failure
    the verifier is there to catch.
    """
    body = None
    if amount is not None:
        body = {"amount": {"value": f"{float(amount):.2f}", "currency_code": currency}}
    return _api("POST", f"/v2/payments/captures/{capture_id}/refund", body)


def cancel_subscription(subscription_id: str, reason: str = "Requested by customer") -> dict:
    """Cancel a subscription. PayPal returns 204 No Content on success."""
    _api("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel", {"reason": reason[:127]})
    return {"status": "CANCELLED"}


# ------------------------------------------------- independent read-backs (the verifier)


def get_refund(refund_id: str) -> dict:
    """PayPal's own record of a refund. status "COMPLETED" = the money really moved."""
    return _api("GET", f"/v2/payments/refunds/{refund_id}")


def get_capture(capture_id: str) -> dict:
    """PayPal's own record of a capture."""
    return _api("GET", f"/v2/payments/captures/{capture_id}")


def get_subscription(subscription_id: str) -> dict:
    """PayPal's own record of a subscription. status is ACTIVE / CANCELLED / SUSPENDED / ..."""
    return _api("GET", f"/v1/billing/subscriptions/{subscription_id}")


# ------------------------------------------------------------------- sandbox seeding
# A refund needs a real captured payment to act on. In sandbox we create an order with a
# test card and capture it, which yields a capture id the refund tools can then refund.
# This needs card payments (Advanced Checkout) enabled on the sandbox BUSINESS account; if
# it is not, seed the capture ids by hand from the PayPal sandbox dashboard instead.

_TEST_CARD = {"number": "4032039999999994", "expiry": "2030-01",
              "name": "Test Buyer", "security_code": "123"}


def _capture_id_from(order: dict) -> str | None:
    try:
        return order["purchase_units"][0]["payments"]["captures"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return None


def create_and_capture_order(amount: float, currency: str = "USD", card: dict | None = None) -> str:
    """Create an order paid by a sandbox test card and capture it; return the capture id."""
    order = _api("POST", "/v2/checkout/orders", {
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": currency, "value": f"{float(amount):.2f}"}}],
        "payment_source": {"card": card or _TEST_CARD},
    })
    # A card order with intent=CAPTURE usually completes on creation; otherwise capture it.
    cap = _capture_id_from(order)
    if cap:
        return cap
    captured = _api("POST", f"/v2/checkout/orders/{order['id']}/capture", {})
    cap = _capture_id_from(captured)
    if not cap:
        raise PayPalError(f"no capture id returned for order {order.get('id')}")
    return cap


def seed_sandbox(store) -> dict:
    """Give the demo orders real sandbox captures so refunds act on real money.

    Idempotent: skips orders that already have a capture or are fully refunded. Returns
    {order_id: capture_id} for what it seeded. Call this once at startup when PAYPAL_READY.
    """
    seeded: dict = {}
    for o in store.list("orders", limit=1000):
        if o.get("paypal_capture_id") or float(o.get("refunded", 0)) >= float(o.get("total", 0)):
            continue
        cap = create_and_capture_order(float(o["total"]))
        store.update("orders", o["id"], {"paypal_capture_id": cap})
        seeded[o["id"]] = cap
    return seeded
