"""Regenerate data/api-snapshot/ from evidence/runs.jsonl, in-process.

    uv run python scripts/snapshot_from_evidence.py

The static site (scripts/build_site.py) reads data/api-snapshot/, which used to be captured by
fetching a live Cloud Run service. There is no Cloud Run any more, so this rebuilds the same
snapshot from the committed sweep (evidence/runs.jsonl) by calling the real FastAPI endpoints
through a TestClient — no server, no network, no GCP. The result is the actual /runs, /metrics
and per-run responses the app would serve for that sweep, so the site shows Refundly's own data.

Note: the sweep persists run records (ticket, plan, claims, verifications/checks), not the raw
per-tool event trail, so run-detail pages show the claim-vs-verifier verdict but a thinner event
log. The headline numbers and every verification are the real ones.
"""
from __future__ import annotations

import os

os.environ.setdefault("ATTEST_PAYPAL_SEED", "0")  # don't try to mint captures at startup
os.environ.setdefault("ATTEST_STORE", "memory")

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from attest_fleet.store import get_store
from attest_fleet.web import app

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "data" / "api-snapshot"
EVID = ROOT / "evidence" / "runs.jsonl"

TOP = [
    ("/health", "health.json"), ("/metrics", "metrics.json"),
    ("/runs/interrupted", "runs__interrupted.json"), ("/approvals", "approvals.json"),
    ("/fleet/identities", "fleet/identities.json"), ("/fleet/playbook", "fleet/playbook.json"),
    ("/briefing", "briefing.json"), ("/openapi.json", "openapi.json"), ("/docs", "docs.html"),
]


def main() -> None:
    recs = [json.loads(l) for l in EVID.read_text().splitlines() if l.strip()]
    if not recs:
        raise SystemExit("evidence/runs.jsonl is empty — run scripts/simulate.py first")

    with TestClient(app) as client:  # runs lifespan: seeds business data
        store = get_store()
        for r in recs:  # load the sweep's runs into the store the endpoints read
            store.set("runs", r["id"], r)

        # Start clean so no predecessor per-run files linger.
        if (SNAP / "runs").exists():
            shutil.rmtree(SNAP / "runs")
        (SNAP / "runs").mkdir(parents=True)
        (SNAP / "fleet").mkdir(parents=True, exist_ok=True)
        # The spoken briefing needs a TTS backend we no longer run; drop any stale audio so the
        # build ships none rather than audio that narrates the old numbers.
        (SNAP / "briefing.wav").unlink(missing_ok=True)

        for path, name in TOP:
            resp = client.get(path)
            resp.raise_for_status()
            (SNAP / name).write_bytes(resp.content)

        runs = client.get("/runs?limit=100&offset=0").json()
        while len(runs["items"]) < runs["total"]:
            page = client.get(f"/runs?limit=100&offset={len(runs['items'])}").json()
            if not page["items"]:
                break
            runs["items"] += page["items"]
        (SNAP / "runs.json").write_text(json.dumps(runs))

        for r in runs["items"]:
            (SNAP / "runs" / f"{r['id']}.json").write_bytes(client.get(f"/runs/{r['id']}").content)
            (SNAP / "runs" / f"{r['id']}.evidence.json").write_bytes(
                client.get(f"/runs/{r['id']}/evidence").content)

    m = json.loads((SNAP / "metrics.json").read_text())
    print(f"snapshot written: {runs['total']} runs into {SNAP}")
    print(f"  silent_failure_rate={m.get('silent_failure_rate')} "
          f"reported={m.get('reported_success_rate')} verified={m.get('verified_success_rate')}")


if __name__ == "__main__":
    main()
