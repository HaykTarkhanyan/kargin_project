# "Public and playable" in the Data API does not mean yt-dlp can fetch it

**Symptom.** Two pool videos, `2jr-BeWAfXc` (Kargin TV, 24 min, "Kargin haxordum / boc
serianer") and `L_YyghytxU0` (M A R C, 108 min, a Voske Dproc compilation), fail every
download with `ERROR: [youtube] <id>: This video is not available`: four attempts each
over 2.2 h on 2026-11-03 (data/compilations/pool_failures.csv), the last ones with
yt-dlp 2026.10.26 and deno installed.

**What the API says.** `videos.list` (data/candidates/status.csv, same day): privacy public,
embeddable, not age-restricted, playable in AM and DE (2jr-BeWAfXc is blocked only in RU).

**Cause.** Unknown. Probably not a stale yt-dlp: the same version fetched the other 254
in-scope pool videos, and the bump to 2026.10.26 had fixed the 403s seen with the older one.

**Consequences.** screen_audio.py records these as `unavailable` in pool_failures.csv, and
map_compilations.py logs them as "no audio" at the start of every pool run. Don't rely on
`status.csv` alone to predict what can be downloaded. If either becomes worth having, try
once with browser cookies before giving up.
