# `npx firebase` under Git Bash on Windows can produce ZERO output and survive its own kill

*From LEARNINGS.md, section "2026-09-06 — Firebase migration (phase 1-3 code)".*

**`npx firebase` under Git Bash on Windows can produce ZERO output and survive its own kill.** Backgrounded or piped, the `.cmd` shim swallowed all emulator output (the emulator was actually running fine), and stopping the shell task killed the shim but left the child node process listening — it later failed a second start with "port 5005 taken". Run the CLI as `node node_modules/firebase-tools/lib/bin/firebase.js ...` from PowerShell instead; output streams normally and the PID you kill is the real one. Clean up strays by port: `Get-NetTCPConnection -LocalPort 5005`.
