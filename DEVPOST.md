# Refundly

**Tagline:** An AI agent that refunds your money through PayPal — and never says "done" until PayPal's own ledger agrees.

---

## Inspiration

Rekha, 58, was double-charged by a gym app she couldn't find the cancel button for. She called,
sat through twenty minutes of hold music, and gave up. Most people give up. The money is small
enough to walk away from and the process is exhausting enough that walking away is the rational
choice. Multiply that by everyone who has ever been quietly overcharged, or trapped in a
subscription built to be un-cancellable, and it is a lot of money that simply stays taken.

An AI agent can do this chore. It can read the complaint, find the charge, and issue the refund.
The thing that kept me up was the failure mode nobody puts on a slide: the agent does the chore
*badly and reports that it did it well.* The refund tool returns `success`, the money never
actually leaves, the agent says "refund issued," its scoreboard stays green, and Rekha still
never gets her money back. The agent is not lying. It read a response that said success and
believed it. It genuinely cannot tell.

I had been looking into exactly this — silent failure in automated systems, the gap between what
a model reports and what actually happened. The research is blunt about the size of it: false
success is up to **48%** of all failures in single-control agent tasks, and the observability
tools that grade an agent with another model as a judge catch it at only about **0.65 AUROC**,
barely better than a coin flip, because a confident wrong claim reads as success to a model too.
Refundly is that research pointed at the one place it hurts a person directly: their money.

## What it does

You describe the problem in plain language — "refund my last charge," "cancel this subscription,
I've been trying for a week." A small governed fleet handles it:

- a **controller** reads the whole request, splits it into typed tasks, and resolves which
  customer you are. It has read-only tools, so the component with the most context has the least
  authority — it cannot move a cent.
- a **billing agent** issues refunds and nothing else. an **account agent** cancels
  subscriptions, changes addresses, locks, unlocks and deletes — and cannot issue a refund.
  The write scopes are disjoint by construction, so a prompt-injected billing agent has no
  cancellation tool to be talked into using.
- a **policy gate** runs before every money action. Refunds over a set limit pause for a human,
  the limit is cumulative per order so five refunds of 98 can't walk through a 100 ceiling, a
  kill switch blocks every write fleet-wide, and irreversible actions always escalate regardless
  of how confident the model is.

Then comes the part the project exists for. After the agent acts, a **verifier re-reads PayPal's
own record** — not the tool's return value, not a local copy — and checks the post-condition the
task implies. A refund is only `verified` when PayPal reports the refund `COMPLETED`; a
cancellation only when PayPal reports the subscription `CANCELLED`. A refund the tool marked
"completed" that PayPal still shows `PENDING` is the silent failure, and it gets caught and
counted instead of shipped. The gap between what the fleet *reported* and what PayPal *confirms*
is published as a rate, next to a hash-linked evidence trail for every request.

**"Done" means PayPal agrees.** That is the whole product in four words.

## Real PayPal, real verification

The agent acts *through the same PayPal client the verifier reads back through*
(`src/attest_fleet/paypal.py`): `refund_capture` and `cancel_subscription` for the actions,
`get_refund`, `get_capture` and `get_subscription` for the independent reads. Using one channel
to act and a second, independent query to confirm is the entire trust argument — the confirmation
does not come from the thing being confirmed. The client is pure-stdlib `urllib`, so verification
adds no dependency, and it talks to the PayPal sandbox over the standard Orders, Payments and
Billing Subscriptions REST APIs.

This is deliberately the layer that neither a payment gateway nor an agent toolkit gives you.
PayPal's own Agent Toolkit already lets an agent *issue* a refund; what nothing in that stack
does is turn around afterward and prove, against the ledger, that the refund really moved. That
proof is Refundly's original contribution.

## Design

A board whose entire argument is "a green light is not evidence" should not itself be a wall of
green. So the console leads with the one number that matters — the **silent-failure rate** — not
a dashboard of reassuring checkmarks. I rebuilt the interface around progressive disclosure: the
Overview tab carries the whole summary, every other tab shows only its own content, and the full
evidence for a request lives in a modal you open on demand rather than a permanent wall of detail.
The palette is restrained to near-monochrome with one blue and a single reserved red for the
silent-failure signal; status is encoded with glyphs as well as colour, so the board is readable
to a colour-blind operator and meets WCAG-AA contrast. It is meant to be scanned under pressure,
not admired.

## Safe failure — the refusal is the feature

In the demo, a customer asks for a $490 annual-plan refund. It does not go through. The gate holds
it before it runs, writes an approval request, and the agent reports `blocked` — never `done`.
That is the behaviour I most want a judge to see first, ahead of any happy path: an agent that is
*allowed* to move real money has to be an agent that stops itself when it should. The same demo
carries a caught silent failure — an address change the tool "saved" to a draft field that the
rest of the system never reads — so you can watch the verifier disagree with a confident `done`
and record it.

## What's real, and what's simulated

The project is about not overstating outcomes, so the submission will not either.

**Real, implemented and committed:** the PayPal sandbox client, the refund/cancel tool wiring,
and the verifier's independent read-back. With sandbox keys set, a refund is marked complete only
if PayPal returns `COMPLETED`. Every model role runs on OpenRouter, and the credential-free test
suite (59 tests, no network) covers the verifier, the policy gate and the metrics. And this has now
been **run live, end to end, on the PayPal sandbox**: the OpenRouter controller planned the ticket
and resolved the right customer by email, the billing agent issued the refund, and the verifier
independently re-read PayPal and confirmed it `COMPLETED` (sandbox refund `5S903169LT367394P`). And
the published numbers are Refundly's own: a 40-ticket OpenRouter evaluation sweep (fault-rate 0.3)
measures a **15.8% silent-failure rate** — reported success 50.0% vs verified 44.7%, every false
"done" caught by the verifier — and the static demo console is built from that sweep.

**Simulated or not yet run live:** the bundled `ATTEST_DEMO` data is fabricated so the interface is
explorable with no backend (the static demo console is **not** — it is the real sweep above). The
sweep's silent failures are **induced with a fault injector**, because a real gateway does not fail
on command; measuring a detection rate needs induced faults, and the single live PayPal-sandbox
refund above is the real-path proof. Minting the demo orders' captures automatically at startup
needs Advanced (direct-card) Checkout on the sandbox business account; where that isn't available,
a capture is minted once via the sandbox buyer-approval flow instead — which is how the live run
above was done.

## A significant update during the hackathon

Refundly is forked from an earlier agent-reliability project of mine, built for a different, now
closed competition. The rules allow an existing project only if it is significantly reworked
during the submission window, and ask that the rework be explained, so here it is exactly.

**Kept:** the governed-fleet spine — a read-only controller, workers with disjoint tool scopes, a
deterministic policy gate, and the idea of verifying post-conditions against a system of record
rather than trusting a self-report.

**Rebuilt in the window:** (1) **real PayPal money movement, verified against PayPal** — the
verifier was re-pointed from a mock in-memory store to PayPal's live ledger, which is what turns
"done means the record agrees" from a tautology into a real claim against a real third party; (2)
the **entire AI backend swapped** from Google Vertex / Gemini to OpenRouter via LiteLLM across the
controller, both workers, the vision intake and the auditor, with the auditor kept on a different
model family (Claude Haiku 4.5) so independent verification stays independent in model as well as
in method; (3) a new **consumer** problem and product — Rekha, not an SRE; (4) a full **UI
overhaul**. The predecessor's Google-Cloud features remain in the code but self-disable without a
project and are not part of this entry's claims.

## Challenges I ran into

The one that still bothers me came from the predecessor and shaped this whole project: a retry
once **double-spent a refund.** The first attempt paid out, the run retried, the second attempt
paid out again, and both verified clean because the end state looked right each time. That is the
exact failure Refundly exists to catch, produced by my own system. The fix is an idempotency
guard that fingerprints a mutating call and replays the recorded result instead of running it
twice, plus the cumulative per-order limit.

Swapping the model backend was more than a config change. The old auditor's independence came
partly from running on a different Google backend; moving everything to OpenRouter meant I had to
re-establish that independence deliberately, by keeping the auditor on a non-Gemini family
(Claude) rather than letting it collapse onto the same model as the workers. I also had to rewrite
the image-intake path onto OpenRouter vision and prove the fleet still boots and passes tests with
no Google credentials anywhere.

And a measurement bug I keep as a cautionary tale: I had been scoring the agent's stated
confidence as if it were the probability the outcome was verified. It isn't — it's the agent's
confidence in *its own claim*, so a worker that says `blocked` at 0.9 is confidently claiming
failure, not success. Fixing that one line changed the calibration numbers materially, and it was
humbling to find it in a project whose entire thesis is "don't trust a number without checking
where it came from."

## Accomplishments I'm proud of

The verification is deterministic and auditable: it reads PayPal and compares, with no model in
the verdict, so a judge who doubts a result can re-read the ledger themselves. The refusal path
works, and I lead with it. The honesty section above exists because a verification layer that
hides its own limits is asking for the very trust it tells you not to give an agent — so I also
measure the checker, and the known blind spot (two customers sharing a name, where an address
write lands and the post-condition passes without confirming it was the right person) is written
down rather than papered over.

## What I learned

Never trust a declared shape — read it from the record. And a retraction is cheaper than a
defense: the credibility of the numbers you keep depends on being willing to drop the ones that
don't hold up.

## What's next

A single live agent-driven refund has been verified against PayPal's sandbox ledger, and a
40-ticket OpenRouter sweep now gives Refundly its own measured silent-failure rate (15.8%); next is
to extend that sweep so every ticket runs against a live sandbox capture end to end, not just the
fault injector. After that: per-agent identity, so each worker acts under its own credential rather
than the process's, and a process-conformance check alongside
end-state verification, so a right outcome reached the wrong way is caught too.

## Built with

OpenRouter, LiteLLM, Google Agent Development Kit (ADK), Claude Haiku 4.5 (independent auditor),
Gemini 2.5 Flash, PayPal REST APIs — Orders, Payments/Refunds, Billing Subscriptions (sandbox),
Python, FastAPI, uv.
