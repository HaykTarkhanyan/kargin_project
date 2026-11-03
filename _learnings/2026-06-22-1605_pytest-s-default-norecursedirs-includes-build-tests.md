# pytest's default `norecursedirs` includes `build` — a `tests/build/` dir is silently skipped on recursion

*From LEARNINGS.md, section "From the codebase-review cleanup (2026-06-22)".*

**pytest's default `norecursedirs` includes `build` — a `tests/build/` dir is silently skipped on recursion.** `pytest tests/build` (explicit path) collected 25 tests; `pytest` / `pytest tests` collected **0** and exited green ("no tests ran"). The default `norecursedirs` (`*.egg .* _darcs build CVS dist node_modules venv {arch}`) matches the literal dir name `build`, so discovery never descends into it. A CI `pytest` step would have passed while testing nothing. Fix: override `norecursedirs` in `[tool.pytest.ini_options]` (and use `testpaths` to keep the frozen `old/` Streamlit app out). General lesson: after wiring a test gate into CI, confirm it actually collects a non-zero count, not just that it exits 0.
