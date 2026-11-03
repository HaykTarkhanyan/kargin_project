# The "Music in this video" panel IS publicly scrapeable

*From LEARNINGS.md, section "Squeezing copyright signal out of YouTube (2026-08-01)".*

**The "Music in this video" panel IS publicly scrapeable**, just not through any API. It sits in `ytInitialData` at `contents.twoColumnWatchNextResults.results.results.contents[].videoSecondaryInfoRenderer.metadataRowContainer.metadataRowContainerRenderer.rows`. Two gotchas: (1) `metadataRowContainer` is a *generic* label→value container YouTube reuses for music, games and other attributions, and the labels vary by video and locale — capture every row verbatim rather than hunting for a "Song" key, or you miss the "Suggested by SME" shape these videos actually use; (2) a watch page is 1.2-1.7 MB but `ytInitialData` closes well before the end, so stream the response and stop at the terminator. Yield here was thin: **17 of 702** (8 UMG, 6 SME, 2 Just Entertainment, 1 Merlin/IDOL).
