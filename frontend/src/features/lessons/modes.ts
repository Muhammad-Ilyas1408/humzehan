import type { LearningMode } from "@/types/api";

export interface ModeInfo {
  value: LearningMode;
  label: string;
  description: string;
}

/** The three learning styles, in display order. Copy says "learning style", never conditions. */
export const LEARNING_MODES: ModeInfo[] = [
  {
    value: "focus",
    label: "Focus",
    description: "Short chunks, each with a key idea and a tick box.",
  },
  {
    value: "easyread",
    label: "Easy-read",
    description: "Short sentences, everyday words and a mini glossary.",
  },
  {
    value: "literal",
    label: "Literal",
    description: "Plain, exact wording in “What it is / How it works” sections.",
  },
];

export function modeLabel(mode: LearningMode): string {
  return LEARNING_MODES.find((m) => m.value === mode)?.label ?? mode;
}
