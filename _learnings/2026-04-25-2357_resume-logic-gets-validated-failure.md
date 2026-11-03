# The resume logic gets validated by failure

*From LEARNINGS.md, section "Concurrency & infra (2026-04-25)".*

**The resume logic gets validated by failure**: a 130-success / 565-fail run was the perfect test for the NaN-handling fix in `load_resume()`. After the fix, restart correctly identified 130 successes and only retried the 565 failures. This is the kind of property you can't unit-test as cheaply as you can validate against real partial-completion state.
