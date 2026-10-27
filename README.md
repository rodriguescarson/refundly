# Refundly

**The refund you never chased — done, and verified against PayPal.**

An AI agent that issues refunds and cancels subscriptions through PayPal, and **never
says "done" until PayPal's own ledger agrees.** Every money action is re-checked against
PayPal's record before the customer is told it happened — because an agent that lies about
moving your money is worse than no agent at all.

> **The one rule:** *Never say it's done until PayPal says so.*

Built for the **PayPal AI Hackathon** (submission window Oct–Nov 2026). Refundly is a
significant, documented rework of an earlier agent-reliability project — see
[How we significantly updated this during the hackathon](#how-we-significantly-updated-this-during-the-hackathon)
for exactly what was rebuilt and why that keeps it eligible.

---

## For judges — try it in two minutes, no keys, no account

Everything below runs on an in-memory store with **no API key, no PayPal account, no cloud.**
You need [`uv`](https://docs.astral.sh/uv/) and Python 3.13+.

```bash
uv sync                                   # install dependencies
uv run pytest -q                          # correctness check: verifier, policy gate, metrics — no network
ATTEST_DEMO=1 ATTEST_STORE=memory uv run uvicorn attest_fleet.web:app --port 8080
```

Open **http://localhost:8080** and you land on the console:

- the **silent-failure rate** — how often the fleet reported a payment "done" that the
  system of record says was *not* done — as the headline number, not an all-green dashboard;
- the **reported-vs-verified gap**: the overstatement the fleet would ship without verification;
- a list of worked requests. Click any one for the full **evidence modal**: the ticket, the
  plan, what the agent claimed, and the **independent read-back from the system of record**
  that confirmed or caught it;
- the caught **silent failure** (an address change the tool "saved" to a draft field the rest
  of the system never reads) and the **pending approval** (a $490 refund held because it
  crosses the auto-approval limit) are both in the sample data, so the interesting cases are
  one click away.

> On **Windows PowerShell**, set the two variables first, then run the server:
> `$env:ATTEST_DEMO='1'; $env:ATTEST_STORE='memory'` then the `uv run uvicorn …` line.

`uv run pytest -q` is the credential-free proof: it exercises the verifier's post-conditions,
the policy gate and the metrics arithmetic with no model and no network in the loop.

---

## The problem

Rekha, 58, was double-charged by a gym app she couldn't find the cancel button for. After
twenty minutes of hold music she gave up — like most people do. Millions of dollars a year
are lost this way: duplicate charges nobody chases, refunds that silently never land,
subscriptions engineered to be un-cancellable.

An AI agent can do this chore. The danger is that it does it *badly and says it did it well.*
When a tool returns `success` but the money never actually moved, the agent reports **refund
issued**, its scoreboard stays green, and Rekha still never gets her money back. Research puts
this **silent-failure** mode at up to **48%** of all failures in single-control agent tasks,
and observability tools that grade an agent with another model as judge catch it at only
**~0.65 AUROC** — barely better than a coin flip, because a confident wrong claim reads as
success to a model too.

## What Refundly does

A plain-language request ("refund my last charge", "cancel this subscription") goes through a
small governed fleet:

```
request ──► controller ──► billing_agent / account_agent ──► PayPal (refund / cancel / capture)
 (ticket)   decomposes,      one task each,                          │
            resolves the     report a Claim                          ▼
            customer                                      verifier: RE-READS PayPal's own
                                                          record, independently of the agent
                                                                     ▼
                                           "done" only if PayPal agrees ── else: silent failure caught,
                                                                            evidence recorded, human escalated
```

- The **controller** sees the whole request and has **read-only** tools: it splits the ask
  into typed tasks and resolves the customer, but cannot move money.
- **Workers have disjoint write scopes.** `billing_agent` can issue refunds and nothing else;
  `account_agent` can cancel subscriptions, change addresses, lock/unlock and delete, and
  cannot issue a refund. A prompt-injected billing agent has no cancellation tool to be talked
  into using.
- A **deterministic policy gate** runs before every money action: refunds above a configurable
  limit ($100 by default) pause for human approval, a kill switch blocks all writes fleet-wide,
  and irreversible actions always escalate regardless of the model's confidence.

## The original layer — verified against PayPal's own ledger

This is the part no payment gateway or agent toolkit provides, and it is what makes Refundly
more than a wrapper around PayPal's API.

After the agent acts, the **verifier re-queries PayPal directly** — not the tool's return
value, not a local mirror — and checks the post-condition the task implies:

- a refund is only `verified` when **`GET /v2/payments/refunds/{id}`** comes back
  `status == "COMPLETED"`;
- a cancellation is only `verified` when **`GET /v1/billing/subscriptions/{id}`** comes back
  `status == "CANCELLED"`.

A refund the tool marked "completed" that PayPal still shows `PENDING` is exactly the silent
failure the verifier exists to catch. **"Done" means PayPal agrees** — and the whole
reported-vs-verified gap is published as a measured rate, next to a hash-linked evidence trail
for every request.

The agent acts through the same PayPal client the verifier reads through
([`src/attest_fleet/paypal.py`](src/attest_fleet/paypal.py)): `refund_capture`,
`cancel_subscription` for the actions; `get_refund`, `get_capture`, `get_subscription` for the
independent read-backs. It is pure-stdlib `urllib`, so it adds no dependency.

## What's real vs what's simulated

The project's whole thesis is about not overstating outcomes, so this README practices it.

**Real — implemented and committed:**

- the PayPal sandbox REST client, the refund/cancel **tool wiring**
  ([`tools.py`](src/attest_fleet/tools.py)) and the verifier's **independent read-back**
  ([`verifier.py`](src/attest_fleet/verifier.py)). With `PAYPAL_CLIENT_ID`/`PAYPAL_SECRET` set,
  `issue_refund` calls PayPal and the run is marked `completed` only if PayPal returns
  `COMPLETED`; otherwise it stays `pending_gateway` and the verifier flags it;
- all model roles run on **OpenRouter** via LiteLLM — no Google Cloud project required;
- the credential-free test suite, and the demo + static console;
- **this path has been run live, end to end, on the PayPal sandbox** (Oct 2026): the OpenRouter
  controller planned the ticket and resolved the customer by email, the billing agent called
  `issue_refund`, and the verifier **independently re-read PayPal** and confirmed the refund
  `COMPLETED` (sandbox refund `5S903169LT367394P`). Model → refund → ledger read-back is proven,
  not just wired;
- the **measured numbers are Refundly's own**: a 40-ticket evaluation sweep on the OpenRouter
  models ([`scripts/simulate.py`](scripts/simulate.py), fault-rate 0.3) reports a **15.8%
  silent-failure rate** — reported success 50.0% vs verified 44.7%; the verifier caught 3 confident
  false "done"s, and one more slipped past it (the genuinely ambiguous two-customers-one-name
  ticket), which is counted as a verifier blind spot rather than hidden
  ([`evidence/summary.json`](evidence/summary.json)). The static console under `site/` is built
  from this sweep.

**Simulated or not yet run live — stated plainly:**

- the bundled demo (`ATTEST_DEMO=1`) is **fabricated sample data**, there so the interface is
  explorable with no backend — but the static console under `site/` is **not**: it is the real
  sweep above;
- the sweep's silent failures are **induced with a fault injector** (`ATTEST_FAULT_RATE`), because
  a real gateway does not fail on command; measuring a *detection* rate needs induced faults, and
  the single live PayPal refund above is the real-path proof;
- when PayPal keys are absent (or an order has no capture), the refund/cancel tools fall back
  to an **in-memory mock** so the app still runs for tests and the demo. The mock preserves a
  fault injector that can simulate a silent failure on demand.
- a live refund needs the demo orders to carry **real sandbox captures** to act on. On a sandbox
  business account with Advanced (direct-card) Checkout these are minted automatically at startup;
  on accounts without it (e.g. some non-US merchants) startup seeding is skipped and a capture is
  minted once via the sandbox **buyer-approval** flow instead (see below) — which is how the live
  run above was done.

## Run it against real PayPal (OpenRouter + sandbox)

```bash
cp .env.example .env
# then fill in, in .env:
#   OPENROUTER_API_KEY   — one key, all model roles      (https://openrouter.ai/keys)
#   PAYPAL_CLIENT_ID     — sandbox app client id         (https://developer.paypal.com/dashboard/applications/sandbox)
#   PAYPAL_SECRET        — sandbox app secret
uv run uvicorn attest_fleet.web:app --port 8080
```

Send a request (this one calls a model and PayPal, so it needs the keys above):

```bash
curl -s "localhost:8080/tickets?wait=1" -H 'content-type: application/json' -d '{
  "customer_ref": "Priya Sharma",
  "subject": "Refund last month",
  "body": "Please refund my Pro monthly charge of 49. My email is priya.sharma@example.com."
}'
```

Then open http://localhost:8080 — the request, the PayPal action, the verifier's read-back and
the evidence trail are all on the board. (The seed data contains two customers named "Priya
Sharma"; the controller disambiguates on the email in the body — the ambiguity is deliberate.)

**Making refunds act on real sandbox money.** A refund needs a real captured payment to act on.
When `PAYPAL_CLIENT_ID`/`PAYPAL_SECRET` are set, the server tries to **mint sandbox captures for the
demo orders at startup** (`paypal.seed_sandbox`, wired into the app lifespan) by paying a test card.
That needs Advanced (direct-card) Checkout on the sandbox **business** account, which isn't available
on every account (e.g. some non-US merchants); when it's unavailable, startup seeding is skipped and
logged and the tools fall back to the in-memory mock. On such an account, mint a capture once through
the sandbox **buyer-approval** flow (create an order, approve it as a sandbox personal account,
capture it), set that `paypal_capture_id` on the order, and run with `ATTEST_PAYPAL_SEED=0` — which
is exactly how the verified live run above was done.

Mutating calls (ticket trigger, kill switch, approvals) are open locally and gated by
`ATTEST_OPERATOR_TOKEN` when it is set; the Google-stack extras from the earlier project
(Model Armor, Agent Registry, Cloud Trace) stay off unless a `GOOGLE_CLOUD_PROJECT` is present,
so none of them is needed to run or judge this entry.

## How we significantly updated this during the hackathon

Refundly is forked from an earlier agent-reliability project of mine (an enterprise customer-ops
fleet built for a *different*, now-closed hackathon). Devpost rules allow an existing project
only if it is **significantly updated during the submission window**, and ask that the update be
explained. Here is exactly what was rebuilt for this entry, and what was kept.

**Kept (the reusable spine):** the governed-fleet architecture — a read-only controller that
decomposes a request, workers with disjoint tool scopes, a deterministic policy gate, and the
*idea* of a verifier that checks post-conditions against a system of record rather than trusting
the agent's self-report — plus the metrics module and the dashboard shell.

**Rebuilt during the window (this is the update):**

1. **Real PayPal money movement, and verification against PayPal.** New `paypal.py` REST client;
   the refund and subscription-cancel tools now call PayPal; and the verifier was **re-pointed
   from a mock in-memory store to PayPal's own ledger**. The system of record is now a real
   third party, which is what makes "done means PayPal agrees" a real claim rather than a
   tautology over a store the agent also wrote. This is the original contribution of the entry.
2. **The entire AI backend was swapped.** Google Vertex AI / Gemini (via `google-genai`) → **OpenRouter**
   via LiteLLM, across the controller, both workers, the vision intake and the auditor. The
   auditor runs on a **different model family** (Claude 3.5 Haiku) from the Gemini-family workers,
   so independent-of-the-worker verification is independent in model as well as in method. The
   image-intake path was rewritten onto OpenRouter vision.
3. **New product and problem framing.** From an enterprise ops console to a consumer refund /
   cancellation advocate (Rekha, not an SRE): a crafted landing page and a rebranded, simplified
   console.
4. **A full UI/UX overhaul:** progressive disclosure (the summary lives only on the Overview
   tab), run detail as a modal, a restrained palette, and WCAG-AA contrast.

**Disclosed honestly:** the earlier project's Google-Cloud features (Model Armor at ingress,
Agent Registry cards, Cloud Trace export) remain in the codebase but **self-disable** without a
GCP project and are **not** part of this entry's claims. The committed metric numbers are now
Refundly's own, from a 40-ticket OpenRouter evaluation sweep (`evidence/summary.json`), replacing
the predecessor's.

## Architecture — where things live

```
src/attest_fleet/
  web.py        HTTP surface: POST /tickets trigger, evidence API, metrics, the console
  fleet.py      the orchestrator: one request through the whole loop, writes single-threaded
  agents.py     ADK agent definitions; models via LiteLlm(OpenRouter)
  tools.py      the tools each worker calls; real PayPal path + in-memory mock fallback
  paypal.py     PayPal sandbox REST client — the agent acts AND the verifier reads back through it
  verifier.py   post-conditions read from PayPal / the store, never from the self-report
  policy.py     the governance gate: kill switch, pre-execution checks, approval thresholds
  metrics.py    reported vs verified, silent-failure rate, calibration, escalation threshold
  experience.py a verified failure becomes a lesson injected into that worker's next run
  store.py      MemoryStore (local/tests) and FirestoreStore behind one interface
  domain.py     the typed contracts (Ticket, Plan, Task, Claim, Verification, Approval)
  config.py     env-driven config: model ids, PayPal keys, thresholds, store backend
  vision.py     multimodal intake: reads an image attached to a request into text
  demo.py       fabricated sample runs for ATTEST_DEMO=1 (memory store only, no model)
  static/       the landing page and the single-file operator console

scripts/build_site.py   builds the static site/ (landing + console snapshot) for GitHub Pages
tests/                  credential-free tests: verifier, policy, metrics, demo guard
```

## Models and PayPal APIs used

| Role | Model (default, override via env) |
|---|---|
| Controller, workers, vision | `openrouter/google/gemini-2.5-flash` |
| Auditor (independent family) | `openrouter/anthropic/claude-haiku-4.5` |
| Transient-error fallback | `openrouter/google/gemini-2.5-flash-lite` |

Every id is overridable (`ATTEST_CONTROLLER_MODEL`, `ATTEST_WORKER_MODEL`,
`ATTEST_AUDITOR_MODEL`, `ATTEST_VISION_MODEL`). PayPal sandbox endpoints used:
Orders (`/v2/checkout/orders`), Payments — refund a capture and read it back
(`/v2/payments/captures/{id}/refund`, `/v2/payments/refunds/{id}`), and Billing Subscriptions
cancel + read-back (`/v1/billing/subscriptions/{id}/cancel`, `/v1/billing/subscriptions/{id}`).

## Roadmap — stated rather than hidden

- Extend the evaluation sweep so every ticket runs against a live sandbox capture end to end (the
  measured rate currently uses fault injection; a single live refund is already proven end to end).
- Per-agent identity (each worker under its own credential), and process-conformance checks in
  addition to end-state verification.

## License

Apache-2.0 — see [LICENSE](LICENSE).
