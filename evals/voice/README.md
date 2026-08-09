# Voice evaluation suite (PHASE 6)

Small representative Spanish audio fixtures for opt-in `real_voice` runs.

Do **not** synthesize the official 5C.2 text dataset into audio here.

Suggested cases (manual / future fixtures under `tests/fixtures/voice/`):

- clean Spanish short phrase
- Colombian colloquial wording
- background noise
- lower volume
- pause-heavy speech
- RED escalation utterance (transcript path)

Automated CI uses stub STT/TTS. Enable real providers with `LIMEN_REAL_VOICE=1`.
