/**
 * Eastern Armenian transliteration to Latin and Cyrillic (phonetic, for search indexing).
 *
 * Rules applied in order:
 *   1. Digraphs (ու, և) — must precede single-char mappings.
 *   2. Single-character mappings.
 * Non-Armenian characters pass through unchanged (lowercased). Both schemes are
 * approximate/phonetic (Armenian has sounds with no exact Latin/Cyrillic letter);
 * fuzzy matching in search.ts bridges the small gaps.
 */

interface Scheme {
  digraphs: Array<[string, string]>;
  single: Record<string, string>;
}

const LATIN: Scheme = {
  digraphs: [["ու", "u"], ["և", "ev"]],
  single: {
    ա: "a", բ: "b", գ: "g", դ: "d", ե: "e", զ: "z", է: "e", ը: "", թ: "t", ժ: "zh",
    ի: "i", լ: "l", խ: "kh", ծ: "ts", կ: "k", հ: "h", ձ: "dz", ղ: "gh", ճ: "ch", մ: "m",
    յ: "y", ն: "n", շ: "sh", ո: "o", չ: "ch", պ: "p", ջ: "j", ռ: "r", ս: "s", վ: "v",
    տ: "t", ր: "r", ց: "ts", ւ: "v", փ: "p", ք: "k", օ: "o", ֆ: "f",
  },
};

const CYRILLIC: Scheme = {
  digraphs: [["ու", "у"], ["և", "ев"]],
  single: {
    ա: "а", բ: "б", գ: "г", դ: "д", ե: "е", զ: "з", է: "э", ը: "", թ: "т", ժ: "ж",
    ի: "и", լ: "л", խ: "х", ծ: "ц", կ: "к", հ: "г", ձ: "дз", ղ: "г", ճ: "ч", մ: "м",
    յ: "й", ն: "н", շ: "ш", ո: "о", չ: "ч", պ: "п", ջ: "дж", ռ: "р", ս: "с", վ: "в",
    տ: "т", ր: "р", ց: "ц", ւ: "в", փ: "п", ք: "к", օ: "о", ֆ: "ф",
  },
};

function transliterate(s: string, scheme: Scheme): string {
  const input = s.normalize("NFC").toLowerCase();
  let out = "";
  for (let i = 0; i < input.length; ) {
    let matched = false;
    for (const [arm, tr] of scheme.digraphs) {
      if (input.startsWith(arm, i)) {
        out += tr;
        i += arm.length;
        matched = true;
        break;
      }
    }
    if (matched) continue;
    const ch = input[i];
    out += Object.prototype.hasOwnProperty.call(scheme.single, ch) ? scheme.single[ch] : ch;
    i++;
  }
  return out;
}

/** Armenian → Latin (e.g. "տոռմուզ" → "tormuz"). */
export function romanize(s: string): string {
  return transliterate(s, LATIN);
}

/** Armenian → Russian-Cyrillic (e.g. "տոռմուզ" → "тормуз"). */
export function cyrillize(s: string): string {
  return transliterate(s, CYRILLIC);
}
