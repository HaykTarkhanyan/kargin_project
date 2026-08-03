/** A track identified in the sketch's audio (Shazam, confirmed matches only). */
export interface Song {
  artist: string; title: string;
  album: string; label: string; released: string;
  /** shazam.com page for the track, "" when absent. */
  url: string;
  /** Second offsets where the track was confirmed. */
  at: number[];
}

export interface Sketch {
  id: string; videoId: string; seq: number | null; title: string;
  url: string; thumbnail: string;
  text: string; textCommon: string;
  actors: string[]; actorsRaw: string; rolesNames: string;
  location: string; languages: string[]; lighting: string;
  durationSec: number | null; viewCount: number | null; uploadDate: string;
  /** Absent on most sketches: song recognition covers only part of the archive. */
  songs?: Song[];
  /**
   * Machine transcript, deliberately separate from `text`: that is a person's
   * transcription, this is machine output with known errors. Present only where
   * it adds dialogue the curation does not already hold — for 95 sketches it is
   * the only dialogue that exists.
   */
  transcript?: Transcript;
}

/** Armenian speech recognised from the sketch's audio. */
export interface Transcript {
  text: string;
  /**
   * "batch_reupload" — we re-uploaded the audio with the language forced to
   * Armenian; "youtube_fetch" — the sketch's own page already had hy captions.
   */
  source: "batch_reupload" | "youtube_fetch";
  events: number;
  armenianChars: number;
  /** Fraction of its sentences that the curated `text` does not already say. */
  novelty: number;
}
