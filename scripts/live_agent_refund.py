"""Full OpenRouter agent-driven refund, end to end, against real PayPal sandbox.

  uv run python scripts/live_agent_refund.py CAPTURE_ID [AMOUNT]

Seeds the demo business data, attaches the real sandbox CAPTURE_ID to Priya's $49 order
(ord_5001), then runs the actual fleet: OpenRouter controller decomposes the ticket ->
billing_agent calls issue_refund (which refunds the real PayPal capture) -> the verifier
INDEPENDENTLY re-reads PayPal's ledger. No agent declares its own success; run.status is
derived from what the verifier found. Prints no secrets.

Needs PAYPAL_CLIENT_ID / PAYPAL_SECRET (sandbox) and OPENROUTER_API_KEY in .env, and an
unrefunded sandbox capture. Where the sandbox business account lacks direct-card checkout, mint
one through the buyer-approval flow (create an order, approve it as the sandbox buyer, capture).
"""
from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys

from attest_fleet import config
from attest_fleet.domain import Ticket
from attest_fleet.fleet import run_ticket
from attest_fleet.store import get_store, seed

ORDER = "ord_5001"            # Priya Sharma, Pro monthly, $49.00, refunded 0
CAP = sys.argv[1]
AMOUNT = float(sys.argv[2]) if len(sys.argv) > 2 else 49.0


def main() -> int:
    print("models:")
    print("  controller:", config.CONTROLLER_MODEL)
    print("  worker    :", config.WORKER_MODEL)
    print("  auditor   :", config.AUDITOR_MODEL, "(independent family)")
    print("  PAYPAL_READY:", config.PAYPAL_READY, " threshold: $%.0f" % config.REFUND_APPROVAL_THRESHOLD)

    store = get_store()
    seed(store)
    # Attach the real, unrefunded sandbox capture to Priya's order so the agent's refund
    # acts on real money (this is what seed_sandbox would do if direct-card worked here).
    store.update("orders", ORDER, {"paypal_capture_id": CAP})
    print(f"\nattached capture {CAP} to {ORDER} (${store.get('orders', ORDER)['total']:.2f})")

    ticket = Ticket(
        id="tkt_live_priya",
        source="email",
        customer_ref="priya.sharma@example.com",
        subject="Please refund my duplicate Pro charge",
        body=("Hi, this is Priya Sharma (priya.sharma@example.com). I was charged $49 for my "
              "Pro monthly plan (order ord_5001) and I'd like a full $49 refund back to my "
              "original payment method. I've been trying to sort this out for a week. Thank you."),
    )

    print("\n--- running the fleet ---")
    run = asyncio.run(run_ticket(ticket))

    print("\n=== RESULT ===")
    print("run.status:", run.status, "  (derived by the verifier, not claimed by any agent)")
    if run.plan:
        print("controller resolution:", run.plan.customer_resolution[:200])
        for t in run.plan.tasks:
            print(f"  task {t.id}: {t.type} -> {t.worker}  order={t.order_id} amount={t.amount}")
    for r in run.results:
        c, v = r.claim, r.verification
        print(f"\n  [{r.task.type} / {r.task.worker}]")
        if c:
            print(f"    agent CLAIM : outcome={c.outcome} confidence={c.confidence}")
            print(f"    actions     : {c.actions}")
            print(f"    evidence    : {c.evidence[:240]}")
        else:
            print("    agent CLAIM : (none - worker error)")
        if v:
            print(f"    VERIFIER    : verified={v.verified} method={v.method} silent_failure={v.silent_failure}")
            print(f"    checks      : {v.detail[:500]}")

    o = store.get("orders", ORDER)
    print("\norder after:", {k: o.get(k) for k in ("total", "refunded", "status", "paypal_capture_id")})
    for rf in store.query("refunds", order_id=ORDER):
        print("refund row :", {k: rf.get(k) for k in ("state", "amount", "paypal_refund_id", "paypal_status")})

    ok = run.status == "verified"
    print("\nVERDICT:", "AGENT REFUND VERIFIED AGAINST PAYPAL." if ok
          else f"run.status={run.status} (see checks above).")
    return 0 if ok else 6


if __name__ == "__main__":
    raise SystemExit(main())
