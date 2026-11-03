# `contentDetails.caption` from `videos.list` flags MANUAL captions only

*From LEARNINGS.md, section "YouTube Data API v3 vs yt-dlp (2026-04-25)".*

**`contentDetails.caption` from `videos.list` flags MANUAL captions only.** For our archive it returned `False` for all 702 videos — that does NOT mean "no captions exist," it means "no human uploaded captions." Auto-captions can still exist (and do, for many videos), and yt-dlp can fetch them. Don't use this field as a pre-filter for "should we fetch transcripts?"
