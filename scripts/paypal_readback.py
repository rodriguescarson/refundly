"""Re-read a refund (and its capture) straight from PayPal's sandbox ledger.

    uv run python scripts/paypal_readback.py REFUND_ID [CAPTURE_ID]

The same independent reads the verifier makes. Prints only ids, statuses, amounts and times.
"""
import json
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()
from attest_fleet import paypal  # noqa: E402

keep = lambda d, ks: {k: d.get(k) for k in ks}
out = {"read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
       "refund": keep(paypal.get_refund(sys.argv[1]), ("id", "status", "amount", "create_time"))}
if len(sys.argv) > 2:
    out["capture"] = keep(paypal.get_capture(sys.argv[2]), ("id", "status", "amount", "create_time"))
print(json.dumps(out, indent=2))
