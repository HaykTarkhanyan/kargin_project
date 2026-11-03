# YouTube will not tell you about third-party copyright claims on videos you do not own

*From LEARNINGS.md, section "Squeezing copyright signal out of YouTube (2026-08-01)".*

**YouTube will not tell you about third-party copyright claims on videos you do not own.** Content ID claims live behind the partner-only [Content ID API](https://developers.google.com/youtube/partner/docs/v1/claims); Data API v3 has no equivalent field; yt-dlp returns 78 fields for these videos with nothing music-, licence- or claim-related among them. Three public proxies exist and are worth fetching anyway: `status.license`, `contentDetails.licensedContent`, `contentDetails.regionRestriction`.
