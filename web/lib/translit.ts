/**
 * Eastern Armenian → Latin romanization.
 *
 * Rules applied in order:
 *   1. Digraph ու → u  (must precede single-char mappings for ու)
 *   2. Ligature և → ev
 *   3. Single-character mappings
 */

// Digraphs first so we don't accidentally split them.
const DIGRAPHS: Array<[string, string]> = [
  ["ու", "u"],
  ["և", "ev"],
];

const SINGLE: Record<string, string> = {
  ա: "a",
  բ: "b",
  գ: "g",
  դ: "d",
  ե: "e",
  զ: "z",
  է: "e",
  ը: "",
  թ: "t",
  ժ: "zh",
  ի: "i",
  լ: "l",
  խ: "kh",
  ծ: "ts",
  կ: "k",
  հ: "h",
  ձ: "dz",
  ղ: "gh",
  ճ: "ch",
  մ: "m",
  յ: "y",
  ն: "n",
  շ: "sh",
  ո: "o",
  չ: "ch",
  պ: "p",
  ջ: "j",
  ռ: "r",
  ս: "s",
  վ: "v",
  տ: "t",
  ր: "r",
  ց: "ts",
  ւ: "v",
  փ: "p",
  ք: "k",
  օ: "o",
  ֆ: "f",
};

/**
 * Romanize an Armenian string to its Latin phonetic equivalent.
 * Non-Armenian characters are passed through unchanged (lowercased).
 */
export function romanize(s: string): string {
  // Normalize to NFC so composite characters are canonical, then lowercase.
  let input = s.normalize("NFC").toLowerCase();
  let result = "";

  for (let i = 0; i < input.length; ) {
    // Try digraphs first.
    let matched = false;
    for (const [arm, lat] of DIGRAPHS) {
      if (input.startsWith(arm, i)) {
        result += lat;
        i += arm.length;
        matched = true;
        break;
      }
    }
    if (matched) continue;

    const ch = input[i];
    if (Object.prototype.hasOwnProperty.call(SINGLE, ch)) {
      result += SINGLE[ch];
    } else {
      result += ch;
    }
    i++;
  }

  return result;
}
