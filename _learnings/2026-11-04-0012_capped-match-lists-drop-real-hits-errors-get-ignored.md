# A capped match list drops real hits, and an ERROR line in an unattended run is never acted on

**Symptom.** audfprint returns hits strongest first, up to `max_returns`. On 2026-11-03 the
pipeline logged `ERROR ... real matches may be cut. Re-match with a higher cap.` 28 times
across an overnight chain, and nothing re-matched them: the chain carried on and the rows
were saved with their tails cut.

**Cause.** Three things:
- A fixed cap is wrong for queries holding many recordings: a 12-min highlight reel
  (`07d2MTZPEmQ`) held 71+ archive pieces, and three fan clips with 25+ re-uploads each
  (`0pp4KFQUPRU` and two more) filled the 25-hit cap with copies, the weakest kept one
  still at 477-688 matched hashes.
- The "is the cut tail real?" test (weakest kept >= 10% of the best) was wrong both ways.
  It fired on queries that matched nothing, such as a 65-min Kaset tape whose best archive
  hit had 20 hashes (`4Hl75htDiGk`): of the 90 saved rows that tripped it, 9 were really
  cut. And it called real hits noise whenever the best hit was huge. In the self-match
  the best hit is the clip matching itself (~2,000 hashes), so every copy under ~200 was
  "noise"; in a compilation one long sketch can hold 20,000.
- **The cap never saved any work.** In audfprint2 `Matcher.match_file` computes every
  hit and then returns `rslts[:self.max_returns]` (matcher.py line 394). My first fix
  re-matched with a doubled cap, which redid the whole analysis for identical results.

**Fix (scripts/audio_index.py, 2026-11-04).** `match()` takes the full list from
`match_hashes()` and keeps every hit with >= 20 matched hashes (`keep_n`), plus the
strongest ones up to the cap. No consumer accepts a hit under 30. Rows that had filled the
cap with a weakest kept hit of >= 20 were re-matched: 2 + 59 candidate rows, 3 archive
compilations (`mrIUW3fCUUo` now keeps 291 hits instead of 103), 1 pool video. No verdict,
cluster or timeline span moved.

**Consequences.** An ERROR that asks a human to re-run something is useless inside a chain
that runs while nobody watches. Either make the code fix the condition itself or stop the
run. Logging and carrying on is the worst of both. And read what a library's limit
actually does before tuning it.
