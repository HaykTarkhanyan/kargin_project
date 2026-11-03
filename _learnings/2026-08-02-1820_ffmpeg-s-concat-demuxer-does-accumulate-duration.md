# ffmpeg's concat demuxer does not accumulate `duration` directives to their sum

*From LEARNINGS.md, section "Batch transcription, and how the Shazam throttle actually behaves (2026-08-02)".*

**ffmpeg's concat demuxer does not accumulate `duration` directives to their sum.** Building a slideshow video from 30 stills with per-entry durations produced **6369 s of video against 6177.5 s of audio** — every card drifting further behind as the video went on. Frame quantisation at 1 fps explains only 14.5 s of that 191.5 s gap. Fix: drop the demuxer and gate each `drawtext` on absolute output time (`enable='between(t,start,end)'`), which reads the timestamp the frame actually carries, so nothing accumulates and nothing drifts. Verified by extracting frames at 1h41m.
