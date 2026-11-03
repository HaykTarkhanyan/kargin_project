# firebase-tools 15 refuses Java < 21 for emulators

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**firebase-tools 15 refuses Java < 21 for emulators.** The machine has system Java 17; instead of upgrading it (something else may depend on 17), a portable Temurin 21 JRE lives at `~/.jdks/jdk-21.0.12.1+1-jre` and gets PATH-prefixed only for emulator runs (`npm run test:rules`). CI installs its own via `actions/setup-java@v4` with `java-version: 21`. Deploys don't need Java at all — only emulators do.
