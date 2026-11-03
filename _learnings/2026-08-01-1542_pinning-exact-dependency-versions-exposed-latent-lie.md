# Pinning exact dependency versions exposed a latent lie in the manifest

*From LEARNINGS.md, section "Duplicate detection by audio fingerprint (2026-08-01)".*

**Pinning exact dependency versions exposed a latent lie in the manifest.** `requires-python = ">=3.10"` had been wrong for a while — the installed numpy 2.4 and pandas 3.0 both require 3.11+, and the venv was already 3.11. With `>=` ranges uv silently resolved something for 3.10; with `==` pins it failed loudly and correctly. Loose ranges hide environment drift rather than tolerating it.
