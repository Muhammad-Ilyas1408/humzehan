import { describe, expect, it } from "vitest";
import { LESSON_LABELS, lessonLabels } from "./labels";

const URDU_LETTER = /[؀-ۿ]/;

describe("lessonLabels", () => {
  it("has the same labels in English and Urdu", () => {
    expect(Object.keys(LESSON_LABELS.ur).sort()).toEqual(Object.keys(LESSON_LABELS.en).sort());
  });

  it("has no empty labels", () => {
    for (const lang of ["en", "ur"] as const) {
      for (const value of Object.values(lessonLabels(lang))) {
        if (typeof value === "string") expect(value.trim()).not.toBe("");
      }
    }
  });

  it("writes Urdu labels in Urdu script", () => {
    const { chunksDone, scoreLine, ...labels } = lessonLabels("ur");
    for (const value of Object.values(labels)) expect(value).toMatch(URDU_LETTER);
    expect(chunksDone(1, 2)).toMatch(URDU_LETTER);
    expect(scoreLine(1, 3)).toMatch(URDU_LETTER);
  });

  it("formats the quiz score as 'score out of total'", () => {
    expect(lessonLabels("en").scoreLine(1, 3)).toBe("Score: 1 out of 3");
    // Urdu "3 میں سے 1" = "1 out of 3"; read right to left it starts with the total.
    expect(lessonLabels("ur").scoreLine(1, 3)).toBe("اسکور: 3 میں سے 1");
  });

  it("keeps Urdu words between the two numbers so they cannot be swapped", () => {
    for (const text of [lessonLabels("ur").scoreLine(1, 3), lessonLabels("ur").chunksDone(1, 3)]) {
      expect(text).toMatch(/3 [؀-ۿ ]+ 1/);
      expect(text).not.toMatch(/\d\s*\/\s*\d/);
    }
  });

  it("formats the chunks-done progress", () => {
    expect(lessonLabels("en").chunksDone(2, 5)).toBe("2 of 5 chunks done");
    expect(lessonLabels("ur").chunksDone(2, 5)).toBe("5 میں سے 2 حصے مکمل");
  });

  it("returns the English labels for English lessons", () => {
    expect(lessonLabels("en").quickQuiz).toBe("Quick quiz");
    expect(lessonLabels("ur").quickQuiz).toBe("مختصر کوئز");
  });
});
