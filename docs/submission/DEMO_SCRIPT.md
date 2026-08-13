# Demo script (spoken + on-screen)

Target length: ~3–5 minutes. Use only features that exist today.

## A. Opening (10–15 s)

**Say:** “LIMEN is a postoperative voice follow-up agent. It listens in Spanish,
checks living clinical knowledge, and escalates when safety rules require it —
the language model never owns the final risk.”

**Show:** Landing or Call screen.

## B. Voice — NORMAL / YELLOW (45–60 s)

**Scenario (demo only — not hard-coded in product):**

Patient: mild wound pain, denies fever (“No tengo fiebre”), asks what to watch.

**Expect:** calm follow-up, no false RED; negation preserved.

**Show:** Call orb / transcript / live context.

## C. Voice — RED escalation (45–60 s)

**Scenario:** “No puedo respirar” / heavy distress phrasing.

**Expect:** RED, escalate, urgent spoken guidance; finish call → escalation
artifact / summary shows escalation.

**Show:** Call → Sessions/Summary or TRAZA safety card.

## D–H. Live knowledge (G5 story) (60–90 s)

1. Open `/knowledge`.
2. Upload a unique harmless text file with a synthetic fact.
3. Wait until **AVAILABLE**.
4. Ask the agent (call or retrieval probe) about that fact.
5. Open TRAZA / probe provenance (document, chunk, page).
6. Delete the document → **REMOVED**.
7. Ask again — fact must be gone.

G5 admin UI already confirmed PASS (2026-08-09); this section is the demo narrative, not a missing gate.

## I. Sessions / summary (20 s)

Show completed call list + structured summary fields (findings, negations,
safety, next steps).

## J. Close (20–30 s)

**Say:** “Safety is deterministic. Knowledge is living and forgettable. Every
decision is inspectable in TRAZA.”

Then answer the two required video questions (see below drafts).

---

## Video question 1 — convince a client

**Draft (speak naturally):**

“After surgery, patients need follow-up that is always available, but hospitals
cannot put a clinician on every routine call. LIMEN gives you a private,
evidence-governed voice agent: it uses your documents with provenance, keeps an
explicit clinical state, and escalates emergencies through a deterministic Safety
Governor — not vibes from a language model. You get TRAZA for audit, live
knowledge you can add or delete without redeploying, and a degraded-safe path if
the LLM is down. That combination — language for conversation, rules for risk —
is what makes adoption responsible.”

## Video question 2 — key technical decision

**Draft:**

“Our key decision was not to let the LLM decide final clinical risk. We
benchmarked the allowed local models on the official advisory set: even Phi-3.5,
the best of the three, only reached about 37.5% RED recall, and the Llama
candidates missed every RED. So we rejected LLM-only triage and cloud-only
shortcuts for the critical path. LIMEN uses Phi for Spanish phrasing under
trusted application state, while Safety Governor remains authoritative. The
risks are rule gaps and extraction errors — with two more weeks we’d deepen
clinical rule validation and finish human voice latency sampling, not replace
the safety architecture.”
