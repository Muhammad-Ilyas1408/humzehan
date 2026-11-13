// Types mirroring the backend schemas (backend/src/humzehan/schemas/).

export type LearningMode = "focus" | "easyread" | "literal";

export interface GlossaryItem {
  term: string;
  meaning: string;
}

export interface QuizItem {
  question: string;
  /** Always 3 options. */
  options: string[];
  /** 0-based index into `options`. */
  answer_index: number;
}

export interface Chunk {
  heading: string;
  /** Markdown. */
  body: string;
  /** Focus mode: the "key idea" (restates a source fact). */
  hook: string | null;
  glossary: GlossaryItem[];
  /** 3 questions per chunk. */
  quiz: QuizItem[];
}

export interface TraceStep {
  node: string;
  note: string;
  ms: number;
}

/** The English lesson an Urdu lesson was translated from (same structure as `chunks`). */
export interface EnglishVersion {
  title: string;
  chunks: Chunk[];
}

export interface Lesson {
  lesson_id: string;
  student: string;
  mode: LearningMode;
  /** True when `title` and `chunks` are in Urdu. */
  urdu: boolean;
  title: string;
  chunks: Chunk[];
  /** Urdu lessons: the original English title and chunks; otherwise null. */
  english: EnglishVersion | null;
  trace: TraceStep[];
  /** ISO 8601 datetime. */
  created_at: string;
}

export interface ProgressCreate {
  lesson_id: string;
  /** >= 0 */
  chunk_index: number;
  /** 0–3 */
  score: number;
}

/** Form fields for POST /api/v1/lessons (text input only). */
export interface CreateLessonInput {
  student: string;
  mode: LearningMode;
  text: string;
  /** Translate the finished lesson into simple Urdu. */
  urdu: boolean;
}

/** Response of POST /api/v1/extract: the text read from a photo. */
export interface ExtractResponse {
  text: string;
}
