export interface Stats {
  totals: { sketches: number; hours: number; views: number; actors: number; from: string; to: string };
  actorsByCount: { name: string; n: number }[];
  actorsAvgViews: { name: string; n: number; avgViews: number }[];
  locationByCount: { loc: string; n: number }[];
  locationAvgViews: { loc: string; n: number; avgViews: number }[];
  durationBuckets: { bucket: string; n: number; avgViews: number }[];
  topViewed: { seq: number | null; id: string; title: string; views: number }[];
  coOccurrence: { actors: string[]; matrix: number[][] };
  topWords: { w: string; n: number }[];
  topPhrases: { p: string; n: number }[];
  composition: { solo: number; duo: number; ensemble: number; uncurated: number };
  viewsHistogram: { bucket: string; n: number }[];
  viewsBySeq: { label: string; avgViews: number }[];
  extremes: { shortestSec: number; shortestSeq: number | null; longestSec: number; longestMin: number };
  nameSuggestions: { name: string; n: number }[];
}
