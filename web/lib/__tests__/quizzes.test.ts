import { describe, it, expect } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { QUIZZES } from "@/lib/quizzes";

// The quiz is hand-written data; these checks catch the typos a compiler cannot:
// a missing option, an answer index off the end, a still that was never cut.
const publicDir = join(__dirname, "..", "..", "public");
const sketchIds = new Set(
  (JSON.parse(readFileSync(join(publicDir, "data", "sketches.json"), "utf8")) as { id: string }[]).map((s) => s.id),
);
const questions = QUIZZES.flatMap((q) => q.questions.map((qq, i) => ({ ...qq, where: `${q.id} #${i + 1}` })));

describe("quiz content", () => {
  it("has something to play", () => {
    expect(QUIZZES.length).toBeGreaterThan(0);
    expect(new Set(QUIZZES.map((q) => q.id)).size).toBe(QUIZZES.length);
    for (const q of QUIZZES) expect(q.questions.length, q.id).toBeGreaterThan(0);
  });

  it("gives every question four distinct options and a valid answer", () => {
    for (const q of questions) {
      expect(q.options, q.where).toHaveLength(4);
      expect(new Set(q.options).size, q.where).toBe(4);
      expect(q.correctIndex, q.where).toBeGreaterThanOrEqual(0);
      expect(q.correctIndex, q.where).toBeLessThan(4);
      if (q.optionImages) expect(q.optionImages, q.where).toHaveLength(4);
    }
  });

  it("points at stills that exist and sketches that are in the archive", () => {
    for (const q of questions) {
      const images = [q.image, ...(q.optionImages ?? [])].filter((x): x is string => !!x);
      for (const img of images) {
        expect(img.startsWith("/quiz/"), `${q.where}: ${img}`).toBe(true);
        expect(existsSync(join(publicDir, img.slice(1))), `${q.where}: ${img} missing`).toBe(true);
      }
      if (q.sketchId) expect(sketchIds.has(q.sketchId), `${q.where}: ${q.sketchId}`).toBe(true);
    }
  });
});
