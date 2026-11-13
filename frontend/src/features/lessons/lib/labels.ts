/** Language of a lesson's content: English, or simple Urdu (F5). */
export type LessonLang = "en" | "ur";

/** The labels shown inside a lesson. The rest of the page always stays English. */
export interface LessonLabels {
  keyIdea: string;
  quickQuiz: string;
  checkAnswers: string;
  /** Quiz result, e.g. "Score: 1 out of 3" / "اسکور: 3 میں سے 1". */
  scoreLine: (score: number, total: number) => string;
  glossary: string;
  chunkDone: string;
  correctYourAnswer: string;
  correctAnswer: string;
  wrongYourAnswer: string;
  /** Focus progress bar, e.g. "2 of 5 chunks done". */
  chunksDone: (done: number, total: number) => string;
}

export const LESSON_LABELS: Record<LessonLang, LessonLabels> = {
  en: {
    keyIdea: "Key idea",
    quickQuiz: "Quick quiz",
    checkAnswers: "Check answers",
    scoreLine: (score, total) => `Score: ${score} out of ${total}`,
    glossary: "Glossary",
    chunkDone: "I’ve finished this chunk",
    correctYourAnswer: "Correct — your answer",
    correctAnswer: "Correct answer",
    wrongYourAnswer: "Your answer — not correct",
    chunksDone: (done, total) => `${done} of ${total} chunks done`,
  },
  ur: {
    keyIdea: "اہم بات",
    quickQuiz: "مختصر کوئز",
    checkAnswers: "جواب چیک کریں",
    // Urdu words between the two numbers, so the bidi algorithm can never swap them
    // (a bare "1 / 3" can show as "3 / 1" inside right-to-left text).
    scoreLine: (score, total) => `اسکور: ${total} میں سے ${score}`,
    glossary: "مشکل الفاظ",
    chunkDone: "میں نے یہ حصہ مکمل کر لیا",
    correctYourAnswer: "درست — آپ کا جواب",
    correctAnswer: "درست جواب",
    wrongYourAnswer: "آپ کا جواب — درست نہیں",
    chunksDone: (done, total) => `${total} میں سے ${done} حصے مکمل`,
  },
};

export function lessonLabels(lang: LessonLang): LessonLabels {
  return LESSON_LABELS[lang];
}
