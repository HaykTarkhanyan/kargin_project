import type { Sketch } from "./types";
import { normalize } from "./search";

export type NameMatch = { sketch: Sketch; kind: "actor" | "mention"; snippet?: string };

const SUFFIXES = new Set(["", "ին", "ի", "ից", "ով", "ում", "ը", "ն", "ներ", "ների", "ներին"]);
const WORD = /[Ա-և]+/gu;

function wordHit(name: string, text: string): boolean {
  const n = normalize(name);
  for (const w of text.toLowerCase().match(WORD) ?? []) {
    if (w === n || (w.startsWith(n) && SUFFIXES.has(w.slice(n.length)))) return true;
  }
  return false;
}

function snippetOf(name: string, sketch: Sketch): string | undefined {
  const n = normalize(name);
  const lines = sketch.lines.length ? sketch.lines : [sketch.text];
  for (const ln of lines) {
    for (const w of ln.toLowerCase().match(WORD) ?? []) {
      if (w === n || (w.startsWith(n) && SUFFIXES.has(w.slice(n.length)))) return ln;
    }
  }
  return sketch.textCommon || undefined;
}

export function findByName(name: string, all: Sketch[]): NameMatch[] {
  if (!normalize(name)) return [];
  const out: NameMatch[] = [];
  for (const s of all) {
    if (wordHit(name, s.actors.join(" ")) || wordHit(name, s.rolesNames)) {
      out.push({ sketch: s, kind: "actor" });
    } else if (wordHit(name, `${s.text} ${s.textCommon}`)) {
      out.push({ sketch: s, kind: "mention", snippet: snippetOf(name, s) });
    }
  }
  return out.sort((a, b) => (b.sketch.viewCount ?? 0) - (a.sketch.viewCount ?? 0));
}
