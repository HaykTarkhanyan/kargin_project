# `response_mime_type="application/json"`

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**`response_mime_type="application/json"`** (passed via `GenerateContentConfig`) is sufficient to get clean JSON without a full pydantic schema — no markdown fences, no preamble. The prompt still has to describe the desired shape; the mime type just constrains the decoder grammar to JSON.
