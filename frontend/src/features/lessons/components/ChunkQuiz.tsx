"use client";

import { useId, useRef, useState } from "react";
import { ApiError, recordProgress } from "@/lib/api";
import type { QuizItem } from "@/types/api";
import { allAnswered, scoreQuiz, type QuizAnswers } from "../lib/quiz";

type SaveState = "idle" | "saving" | "saved" | "error";

interface ChunkQuizProps {
  lessonId: string;
  chunkIndex: number;
  quiz: QuizItem[];
}

export function ChunkQuiz({ lessonId, chunkIndex, quiz }: ChunkQuizProps) {
  const id = useId();
  const [answers, setAnswers] = useState<QuizAnswers>(() => quiz.map(() => null));
  const [checked, setChecked] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  // Guards against sending the score twice (e.g. a double click).
  const sending = useRef(false);

  if (quiz.length === 0) return null;

  const score = scoreQuiz(quiz, answers);

  async function save(value: number) {
    if (sending.current) return;
    sending.current = true;
    setSaveState("saving");
    try {
      await recordProgress({ lesson_id: lessonId, chunk_index: chunkIndex, score: value });
      setSaveState("saved");
      // Stays true: the score is saved once per chunk.
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Your score could not be saved.");
      setSaveState("error");
      sending.current = false;
    }
  }

  function handleCheck() {
    if (checked || !allAnswered(quiz, answers)) return;
    setChecked(true);
    void save(score);
  }

  return (
    <section aria-labelledby={`${id}-title`} className="mt-6 border-t border-border pt-5">
      <h4 id={`${id}-title`} className="text-lg font-semibold">
        Quick quiz
      </h4>
      <div className="mt-3 flex flex-col gap-5">
        {quiz.map((item, qi) => (
          <fieldset key={qi} disabled={checked} className="flex flex-col gap-2">
            <legend className="mb-2 font-semibold">
              {qi + 1}. {item.question}
            </legend>
            {item.options.map((option, oi) => {
              const chosen = answers[qi] === oi;
              const correct = oi === item.answer_index;
              let tone = chosen ? "border-accent bg-accent-soft" : "border-border bg-surface";
              let tag = "";
              if (checked && correct) {
                tone = "border-success bg-success-soft";
                tag = chosen ? "Correct — your answer" : "Correct answer";
              } else if (checked && chosen) {
                tone = "border-danger bg-danger-soft";
                tag = "Your answer — not correct";
              }
              return (
                <label
                  key={oi}
                  className={`flex min-h-12 items-center gap-3 rounded-lg border-2 px-4 py-2 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${tone} ${
                    checked ? "cursor-default" : "cursor-pointer"
                  }`}
                >
                  <input
                    type="radio"
                    name={`${id}-q${qi}`}
                    checked={chosen}
                    onChange={() =>
                      setAnswers((prev) => prev.map((a, i) => (i === qi ? oi : a)))
                    }
                    className="h-5 w-5 shrink-0 accent-accent focus-visible:outline-none"
                  />
                  <span className="flex-1">{option}</span>
                  {tag && (
                    <span
                      className={`text-sm font-semibold ${correct ? "text-success" : "text-danger"}`}
                    >
                      {tag}
                    </span>
                  )}
                </label>
              );
            })}
          </fieldset>
        ))}
      </div>

      {!checked ? (
        <button
          type="button"
          onClick={handleCheck}
          disabled={!allAnswered(quiz, answers)}
          className="mt-5 min-h-12 rounded-lg bg-accent px-6 font-semibold text-white hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
        >
          Check answers
        </button>
      ) : (
        <div className="mt-5 flex flex-col gap-2" aria-live="polite">
          <p className="text-lg font-semibold">
            Score: {score} / {quiz.length}
          </p>
          {saveState === "saving" && <p className="text-sm text-muted">Saving your score…</p>}
          {saveState === "saved" && <p className="text-sm text-success">Score saved.</p>}
          {saveState === "error" && (
            <div role="alert" className="rounded-lg border border-danger bg-danger-soft p-3">
              <p className="text-sm">
                <span className="font-semibold text-danger">Your score wasn’t saved.</span>{" "}
                {saveError}
              </p>
              <button
                type="button"
                onClick={() => void save(score)}
                className="mt-2 min-h-11 rounded-lg border border-danger bg-surface px-4 text-sm font-semibold text-danger"
              >
                Retry saving
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
