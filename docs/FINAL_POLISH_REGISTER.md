# FINAL POLISH register

Deferred work after PHASE 10 submission package. **Do not start FINAL POLISH
in PHASE 10.**

## P0 — gate / eliminatory evidence

- G4 human browser mic → audible playback (multi-turn)
- G4 official speech-end→playback P50/P95 (`FINAL_EVIDENCE_REQUIRED:G4_P50/P95`)
- G5 admin UI upload→use→delete→forget confirmation — **DONE** 2026-08-09 (operator UI + API evidence PASS)
- Demo video recording (`FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO`)
- Optional but recommended: strict cold clone G2 (`FINAL_EVIDENCE_REQUIRED:G2_STRICT_CLONE`)

## P1 — scoring / truthfulness

- Full official corpus 107/107 ingest verification (`FINAL_EVIDENCE_REQUIRED:OFFICIAL_CORPUS_FULL`)
- Real token usage populated in README metrics when provider reports it
- Cost/call with verified price source (`FINAL_EVIDENCE_REQUIRED:COST_CALL`)
- Screenshot package for final report
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
