# YouTube's `automatic_captions` dict mostly contains auto-translations, not source captions

*From LEARNINGS.md, section "From the metadata-fetch (2026-04-25)".*

**YouTube's `automatic_captions` dict mostly contains auto-translations, not source captions.** The single key ending in `-orig` (e.g. `ru-orig`) marks the language YouTube actually transcribed in. Everything else is derived. Parse `-orig` to get `auto_caption_source_lang`.
