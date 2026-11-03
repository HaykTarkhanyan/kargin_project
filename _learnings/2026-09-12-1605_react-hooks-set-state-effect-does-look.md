# `react-hooks/set-state-in-effect` does not look inside a local function, so a clean lint is not proof

*From LEARNINGS.md, section "2026-09-12 — collections, and four things that looked like bugs but were not".*

**`react-hooks/set-state-in-effect` does not look inside a local function, so a clean lint is not proof.** `useEffect(() => { const sync = () => setX(read()); sync(); ... })` passes; inlining the same call as `useEffect(() => { setX(read()) })` is an error. The rule is right and the indirection was hiding it. For `localStorage` state on a statically exported page the answer is `useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)`: the server snapshot is what both the export and the hydration render use, so there is no mismatch and no effect at all. `getSnapshot` must return a primitive — returning the `Set` itself changes identity every read and loops forever. `SearchExperience` still uses the older pattern and still passes lint.
