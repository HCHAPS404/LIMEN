# Manual conversation evaluation — PHASE 6.3

Use during real browser voice runs. Do **not** invent rows.

For each turn record:

| # | call_id | turn_id | scenario | patient finished before assistant? | transcript OK? | response relevant to current+prior? | unnecessary repetition? | re-asked answered Q? | interruption? | interruption handled OK? | SafetyDecision OK? | audible? | latency sample valid? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| … |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 20 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

Scenarios to cover (at least once):

- Normal 3–4 turn conversation
- `como un siete` after pain question
- Pause-heavy Spanish
- Patient interrupts LIMEN
- Patient interrupts RED instruction
- Document-grounded
- No-evidence
- Turns 2–4 without re-greeting

Aggregate checklist (manual):

- [ ] Context survives ≥4 turns
- [ ] Answered questions not re-asked
- [ ] False barge-in rare / controlled
- [ ] Real barge-in stops audio quickly
- [ ] RED interrupted still delivers urgency
- [ ] ≥20 valid browser latency samples recorded separately

Latency validity: exclude failed turns, false endpoints, stale audio, cancelled responses.
