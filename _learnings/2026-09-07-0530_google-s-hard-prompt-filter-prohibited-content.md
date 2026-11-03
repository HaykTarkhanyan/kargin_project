# Google's hard prompt filter (`PROHIBITED_CONTENT`) triggers on PHRASE COMBINATIONS across prompt + data, deterministically

*From LEARNINGS.md, section "2026-09-07 — Gemini extraction pilot (Vertex AI)".*

**Google's hard prompt filter (`PROHIBITED_CONTENT`) triggers on PHRASE COMBINATIONS across prompt + data, deterministically.** Seq 582 ("naked models" sketch) passed under the v1 prompt but was blocked 3/3 times under v2 — the trigger was the instruction phrase "male actors play female roles" colliding with that transcript's content. Rewording the instruction ("appear in drag") fixed it without touching the data. This is `prompt_feedback.block_reason`, NOT candidate safety — `safety_settings` can't disable it; rephrase or drop the offending fragment. Also: `response.text` is None then, so error messages must guard against `None[:500]`.
