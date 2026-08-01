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
}
