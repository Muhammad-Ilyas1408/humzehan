import { describe, expect, it } from "vitest";
import type { QuizItem } from "@/types/api";
import { allAnswered, scoreQuiz } from "./quiz";

const quiz: QuizItem[] = [
  { question: "Q1", options: ["a", "b", "c"], answer_index: 0 },
  { question: "Q2", options: ["a", "b", "c"], answer_index: 1 },
  { question: "Q3", options: ["a", "b", "c"], answer_index: 2 },
];

describe("scoreQuiz", () => {
  it("scores 3 when every answer is correct", () => {
    expect(scoreQuiz(quiz, [0, 1, 2])).toBe(3);
  });

  it("counts only correct answers", () => {
    expect(scoreQuiz(quiz, [0, 0, 0])).toBe(1);
    expect(scoreQuiz(quiz, [2, 2, 1])).toBe(0);
  });

  it("treats unanswered questions as wrong", () => {
    expect(scoreQuiz(quiz, [0, null, 2])).toBe(2);
    expect(scoreQuiz(quiz, [])).toBe(0);
  });
});

describe("allAnswered", () => {
  it("is true only when every question has an answer", () => {
    expect(allAnswered(quiz, [0, 1, 2])).toBe(true);
    expect(allAnswered(quiz, [0, null, 2])).toBe(false);
    expect(allAnswered(quiz, [0, 1])).toBe(false);
  });
});
