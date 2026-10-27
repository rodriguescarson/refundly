# Refundly — demo video script & storyboard

**Target length:** under 3:00 (aim 2:45, leaving buffer). **Language:** English.
**Format:** screen capture of the console + PayPal sandbox, single continuous take for the
live beats, calm voiceover. **On-screen banner (top-right, whole video): `LIVE RUN · NO CUTS`.**

**Voiceover budget:** ~400 words at ~145 wpm. The script below is ~395. Speak unhurried; silence
over the proof shots is fine.

**Recording setup**
- Screen-record the console at 1280×900 (the width the layout is tuned for); light theme reads
  best on video. Browser zoom 100%.
- Keep the browser **address bar visible** whenever PayPal or the console is on screen — the URL
  is the proof it is real.
- Add captions/subtitles (accessibility, and many judges watch muted).
- Record VO separately and lay it under the capture; do not narrate live while clicking.

> **Honesty switch.** Beats 3–4 assume the live PayPal sandbox run is wired (`seed_sandbox` at
> startup, keys in `.env`). If you film **before** that, use the **[pre-live]** alternate lines
> marked in those beats: demo the sandbox integration on seeded data and say so plainly. Never
> show a PayPal dashboard you did not actually transact against.

---

## Beat 1 — Cold open: the person (0:00–0:18)

- **Screen:** full-bleed title card, near-black on white. Large: *"Rekha, 58. Double-charged by an
  app she couldn't cancel."* Below, smaller: *"She called. Twenty minutes of hold music. She gave
  up — like most people do."* Fade to the Refundly wordmark.
- **VO:** "Rekha was charged twice by a gym app she couldn't find the cancel button for. She
  called, waited on hold, and gave up — the way most of us do. The money stays taken. An AI agent
  could fix this for her. The problem is what happens when it fixes it *badly* — and tells her it
  worked."
- **On-screen text (end of beat):** `Never say it's done until PayPal says so.`

## Beat 2 — What it is, in one screen (0:18–0:34)

- **Screen:** console **Overview** tab loads. Cursor rests on the hero: the big **silent-failure
  rate** number, then the Reported-vs-Verified bars.
- **VO:** "This is Refundly. It issues refunds and cancels subscriptions through PayPal — and it
  leads with the one number nobody else shows: how often an agent reports a payment *done* that
  the ledger says never happened. The gap between what it claimed and what PayPal confirms."
- **On-screen text:** `Reported ≠ Verified`

## Beat 3 — The refusal, first (0:34–1:06)

> Shown before any success on purpose: an agent allowed near real money has to stop itself.

- **Screen:** paste a request into the trigger — *"Refund my annual plan, $490."* Submit. The run
  appears; open its modal. The claim reads **blocked**, and an **approval card** is waiting in the
  Approvals tab. Hover the policy event: *refund 490.00 exceeds the 100 auto-approval limit.*
- **VO:** "Watch what it does *before* it does anything right. A four-hundred-and-ninety-dollar
  refund. Refundly doesn't pay it. The policy gate stops it, routes it to a human, and the agent
  reports *blocked* — not done. The limit is cumulative per order, so you can't sneak a big refund
  through as small ones. The refusal is the feature."
- **On-screen text:** `Over the limit → held for a human. Agent says "blocked", never "done".`

## Beat 4 — The happy path, and the proof (1:06–1:46)

- **Screen:** submit *"Refund my last Pro charge, $49"* for Priya. The run goes **verified**.
  **Cut to the PayPal sandbox dashboard** (address bar on `sandbox.paypal.com`) showing the
  matching refund, `COMPLETED`, same amount. Cut back to the console modal: the **independent
  read-back from PayPal** line, green.
- **VO:** "Now a real one. A forty-nine-dollar refund goes out. Here it is on PayPal's own sandbox
  dashboard — same amount, completed. And back in Refundly, the verdict doesn't come from the
  agent. It comes from re-reading PayPal's record, independently. That read-back is what makes
  *done* mean something."
- **VO [pre-live alternate]:** "Now a real one. The refund goes out through the PayPal client, and
  Refundly confirms it by re-reading PayPal's own record — not the agent's word. This run uses
  seeded sandbox data; the live transaction sweep is the last step before submission, and the
  verification path you're watching is the real one."
- **On-screen text:** `"Done" = PayPal's ledger agrees — not the agent's say-so.`

## Beat 5 — The catch: a silent failure (1:46–2:22)

- **Screen:** open the run that resolved **silent failure** (the address change "saved" to a draft
  field). In the modal: the agent's claim is **done** at high confidence; the **independent check**
  is red — *address is still the old one.* Scroll to the evidence trail.
- **VO:** "And this is why it exists. Here the agent was *sure*. It claimed done, at ninety-five
  percent confidence. But the write landed in a draft field the system never reads — the money, or
  the change, never actually moved. A normal dashboard shows this green. Refundly caught it,
  marked it a silent failure, and kept the evidence. Research puts this failure at up to half of
  all agent failures, and model-judge tools barely beat a coin flip at spotting it. A
  deterministic read of the record doesn't miss it."
- **On-screen text:** `Confident. Wrong. Caught.`

## Beat 6 — Honest, by design (2:22–2:38)

- **Screen:** back to Overview; cursor on the Reported-vs-Verified gap and the escalation line.
- **VO:** "It's honest about itself, too. It publishes the gap, it escalates what it's unsure of to
  a person, and it even reports where its *own* checker has blind spots. A verification layer that
  hid its limits would be asking for the exact trust it tells you not to give an agent."
- **On-screen text:** `Measures the agent. Measures the checker.`

## Beat 7 — Close (2:38–2:55)

- **Screen:** Refundly wordmark, centered. Below: the thesis line, then `github.com/rodriguescarson/refundly`
  and the category tags.
- **VO:** "Refundly. The refund you never chased — done, and verified against PayPal. Never say
  it's done until PayPal says so."
- **On-screen text:**
  `Refundly · OpenRouter + Google ADK + PayPal (sandbox)`
  `Best Use of Agentic Commerce · Best Use of PayPal + AI`

---

## Claim-to-proof ledger (write this before you film)

Every spoken claim should map to something visible on screen. Do not say a thing the frame can't back.

| Claim in VO | On-screen proof |
|---|---|
| "leads with the silent-failure number" | Overview hero number |
| "$490 refund is refused / held for a human" | run modal `blocked` + approval card + policy event |
| "cumulative per order" | (optional) tooltip / README line, don't belabor on camera |
| "$49 refund completed on PayPal" | **PayPal sandbox dashboard**, address bar visible, `COMPLETED` |
| "verdict comes from re-reading PayPal" | modal's independent read-back line, green |
| "caught a confident silent failure" | silent-failure run modal: claim `done` 0.95 vs red check |
| "publishes the gap / escalates / reports blind spots" | Overview gap + escalation line (README for blind spots) |

## Shot checklist

- [ ] `LIVE RUN · NO CUTS` banner present the whole video
- [ ] Address bar visible on every console and PayPal frame
- [ ] Refusal shown **before** the successful refund
- [ ] PayPal sandbox dashboard proof shot (or the **[pre-live]** honest alternate)
- [ ] Captions burned in
- [ ] Total runtime under 3:00 (target 2:45)
- [ ] No real customer data; sandbox and seeded demo data only
