# WebM is NOT in Google's documented supported audio formats

*From LEARNINGS.md, section "Gemini STT spike (2026-04-26)".*

**WebM is NOT in Google's documented supported audio formats** (WAV, MP3, AIFF, AAC, OGG Vorbis, FLAC). Transcode webm/opus → ogg/vorbis with `ffmpeg -i in.webm -vn -c:a libvorbis -q:a 4 out.ogg` before upload. Quality 4 vorbis is plenty for STT and shrinks the upload (~30-50% of the webm size).
