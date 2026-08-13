# FINAL POLISH register

Deferred work after PHASE 10 submission package. **Do not start FINAL POLISH
in PHASE 10.**

## P0 — gate / eliminatory evidence

- G4 human browser mic → audible playback (multi-turn) — **DONE** 2026-08-09
- G4 official speech-end→playback P50/P95 — **DONE** 2026-08-12 (warm N=84; 6457 / 19103 ms; `docs/G4_VOICE_GATE.generated.md`)
- G5 admin UI upload→use→delete→forget confirmation — **DONE** 2026-08-09 (operator UI + API evidence PASS)
- Demo video recording — **DONE** **https://youtu.be/CAO7SUBaV2s**
- Optional but recommended: strict cold clone G2 — **DONE** 2026-08-12 (`docs/G2_BOOTSTRAP.generated.md`; 290.52s PASS; git worktree HEAD; pip/npm/HF isolated)

## P1 — scoring / truthfulness

- Full official corpus 107/107 ingest verification — **DONE** 2026-08-12 (`docs/OFFICIAL_CORPUS.generated.md`; 107/107 AVAILABLE, ingest directo)
- Real token usage populated in README metrics when provider reports it — **DONE** 2026-08-12 (`docs/EVAL_RESULTS.generated.md`)
- Cost/call with verified price source — **DONE** 2026-08-12 (`docs/COST_CALL.generated.md`; OpenAI list price 2026-08-12)
- Screenshot package for final report — **DONE** 2026-08-12 (S01–S06 under `docs/submission/assets/`)
- Public repo push confirmation (`FINAL_EVIDENCE_REQUIRED:PUBLIC_REPO_PUSH`)

## P2 — functional polish

- Conversation phrasing / repetition tuning — **DONE** 2026-08-09 (preferred name, usted, anti-3ª persona, prompt v7)
- Piper multi-persona voices (Elena/Nikolas/Anikka/Alex) selectable in Settings — **DONE** 2026-08-09 (gender+name in chat only; Piper packs local)
- Piper naturalness knobs + Anikka→es_MX-claude-high (LatAm; no official es_CO) — **DONE** 2026-08-09 (age is persona label; Piper cannot invent youth)
- Piper latency optimization — deferred; prosody/silence/fades tuned same day (no latency claim)
- VAD leading-syllable pre-roll + barge-in/echo holdoff — **DONE** 2026-08-09 (human re-check still needed)
- Opening greeting no longer uses GREEN clinical boilerplate — **DONE** 2026-08-09
- Truncated LLM words / usted / no fake booking offers — **DONE** 2026-08-09 (validator + repair + prompt v8)
- STT CO lexicon bias + conservative transcript repairs — **DONE** 2026-08-09 (not full dialect ASR)
- Talkative endpointing (~1.9s silence, 90s max) — **DONE** 2026-08-09
- Mood distress lexical finding + empathy prompt guidance — **DONE** 2026-08-09
- Call lifecycle: identity assistant≠patient, farewell/reunión hang-up, idle/max-duration — **DONE** 2026-08-09
- Demo UX clarity (without redesign)

## P3 — visual

- Landing/call visual refinements
- Diagram PNG export styling

## P4 — post-challenge

- AudioWorklet migration
- Broader clinical validation
- Hospital integration (explicitly out of challenge critical path)
