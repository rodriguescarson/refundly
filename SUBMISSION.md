# Submission status — PayPal AI Hackathon

**Submitted** on Devpost, 2026-10-27. Edits stay open until **Nov 12, 2026, 12:00 PT** (Nov 13, 01:30 IST). Judging runs Dec 1–15.

## Where everything lives

| What | Link |
| --- | --- |
| Devpost entry (submission 1268020) | https://devpost.com/software/refundly |
| Demo video, 2:55, public | https://youtu.be/OP1T5kTTRF8 |
| Live console (GitHub Pages) | https://rodriguescarson.github.io/refundly/ (console at `app.html`) |
| Repo (public, Apache-2.0) | https://github.com/rodriguescarson/refundly, branch `paypal-ai-hackathon` |

The same video is in the repo at `media/refundly-demo.mp4`, and the poster frame is at `media/refundly-demo.jpg`.

## What the entry claims (keep later edits consistent)

- Live sandbox proof: refund `5S903169LT367394P` (COMPLETED, $49) on capture `6CY87396F12807001`. Rerun it with `scripts/live_agent_refund.py` and read it back with `scripts/paypal_readback.py`.
- Sweep numbers: 15.8% silent-failure rate, 50.0% reported vs 44.7% verified, 3 false "done"s caught, 1 slipped (the verifier's blind spot). Don't write "every false done caught".
- PayPal is used through its REST APIs in sandbox, not the Agent Toolkit or disputes.
- AI tools: Gemini 2.5 Flash for the controller and workers, Claude Haiku 4.5 as the auditor, and Gemini vision. No model decides the money verdict. In the video only, the narration is OpenRouter `openai/gpt-audio` (voice marin) and the music is `google/lyria-3-pro-preview`.
- `DEVPOST.md` mirrors the story text on Devpost. Change both together.

## How the video was built

It was made with the brag-slim method. The workspace is `brag-output/` (gitignored): the plan, narration, timeline, compose page, render and mix scripts, and the Devpost gallery images in `brag-output/devpost/`. Cuts snap to the music's beat grid (89.1 BPM). The mix is loudness-normalized to -16 LUFS.

## Optional extras (none required)

- [ ] A custom YouTube thumbnail: upload `brag-output/brag.jpg` in YouTube Studio.
- [ ] If "Rekha, 58" isn't a real person, label her as a composite in the Devpost story, `DEVPOST.md` and the video description.
- [ ] Any edit before the deadline goes through **Edit** on the Devpost submission.

## Gotchas

- GitHub Actions (CI and Pages) only run because the repo is public. Account billing blocks private-repo minutes.
- Site URLs must stay relative, because Pages serves from `/refundly/`. `scripts/build_site.py` writes them that way.
- `.env` holds the real sandbox and OpenRouter keys. It is gitignored and was never committed. A full history scan ran before the repo went public.
