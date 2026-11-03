# YouTube's `contentDetails.caption` field flags MANUAL captions only

*From LEARNINGS.md, section "YouTube transcript fetch (2026-04-26)".*

**YouTube's `contentDetails.caption` field flags MANUAL captions only.** For our archive it's `False` for all 702, but auto-captions exist for 314. Don't use this field as a "should we try fetching transcripts?" pre-filter — it'll incorrectly drop most of the data.
