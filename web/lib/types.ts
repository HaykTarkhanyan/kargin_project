export interface Sketch {
  id: string; videoId: string; seq: number | null; title: string;
  url: string; thumbnail: string;
  text: string; textCommon: string;
  actors: string[]; actorsRaw: string; rolesNames: string;
  location: string; languages: string[]; lighting: string;
  durationSec: number | null; viewCount: number | null; uploadDate: string;
}
