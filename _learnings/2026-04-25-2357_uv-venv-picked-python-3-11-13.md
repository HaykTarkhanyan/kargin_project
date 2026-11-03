# `uv venv` picked Python 3.11.13 over the system 3.10.10

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**`uv venv` picked Python 3.11.13 over the system 3.10.10** when `requires-python = ">=3.10"` is set. uv prefers newer Pythons it has access to. Pin a specific minor if reproducibility matters.
