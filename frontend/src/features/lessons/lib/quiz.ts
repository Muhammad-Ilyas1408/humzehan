import type { QuizItem } from "@/types/api";

/** One answer per question: the chosen option index, or null if not answered. */
export type QuizAnswers = (number | null)[];

/** Number of correct answers; unanswered questions count as wrong. */
export function scoreQuiz(quiz: QuizItem[], answers: QuizAnswers): number {
  return quiz.reduce((score, item, i) => (answers[i] === item.answer_index ? score + 1 : score), 0);
}

export function allAnswered(quiz: QuizItem[], answers: QuizAnswers): boolean {
  return quiz.every((_, i) => answers[i] !== null && answers[i] !== undefined);
}
