"use client";

import { useState } from "react";
import type { Lesson } from "@/types/api";
import { isolateLtr } from "../lib/bidi";
import { lessonLabels, type LessonLang } from "../lib/labels";
import { modeLabel } from "../modes";
import { ChunkCard } from "./ChunkCard";

/** Remount with key={lesson.lesson_id} so tick boxes reset for a new lesson. */
export function LessonView({ lesson }: { lesson: Lesson }) {
  const [done, setDone] = useState<boolean[]>(() => lesson.chunks.map(() => false));
  const [showEnglish, setShowEnglish] = useState(false);

  // Urdu lessons carry the English version too; the student can switch between them.
  const english = lesson.urdu ? lesson.english : null;
  const lang: LessonLang = english && !showEnglish ? "ur" : "en";
  const urdu = lang === "ur";
  const content = english && showEnglish ? english : lesson;
  const labels = lessonLabels(lang);
  const dirProps = urdu ? { lang: "ur", dir: "rtl" as const } : { lang: "en", dir: "ltr" as const };

  const doneCount = done.filter(Boolean).length;
  const total = content.chunks.length;

  return (
    <section aria-labelledby="lesson-title" className={`mode-${lesson.mode} flex flex-col gap-5`}>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold uppercase tracking-wide text-muted">
            {modeLabel(lesson.mode)} learning style
            {english && " · Simple Urdu"}
          </p>
          <h2
            id="lesson-title"
            {...dirProps}
            className={`mt-1 text-2xl font-semibold sm:text-3xl ${urdu ? "lesson-urdu" : ""}`}
          >
            {urdu ? isolateLtr(content.title) : content.title}
          </h2>
        </div>
        {english && (
          <button
            type="button"
            onClick={() => setShowEnglish((value) => !value)}
            aria-pressed={showEnglish}
            className="min-h-11 rounded-lg border-2 border-accent bg-surface px-4 font-semibold text-accent-strong hover:bg-accent-soft"
          >
            {showEnglish ? "Show Urdu" : "Show English"}
          </button>
        )}
      </header>

      {/* Same elements in both languages (only attributes change), so tick boxes and quiz
          answers are kept when switching. */}
      <div {...dirProps} className={`flex flex-col gap-5 ${urdu ? "lesson-urdu" : ""}`}>
        {lesson.mode === "focus" && total > 0 && (
          <div className="sticky top-0 z-10 rounded-xl border border-border bg-surface px-5 py-3">
            <label htmlFor="focus-progress" className="text-sm font-semibold">
              {labels.chunksDone(doneCount, total)}
            </label>
            <progress
              id="focus-progress"
              max={total}
              value={doneCount}
              className="mt-2 block h-3 w-full overflow-hidden rounded-full [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-accent-soft [&::-webkit-progress-value]:bg-accent"
            />
          </div>
        )}

        {content.chunks.map((chunk, i) => (
          <ChunkCard
            key={i}
            lessonId={lesson.lesson_id}
            mode={lesson.mode}
            chunk={chunk}
            index={i}
            done={done[i] ?? false}
            onDoneChange={(value) => setDone((prev) => prev.map((d, j) => (j === i ? value : d)))}
            lang={lang}
            labels={labels}
          />
        ))}
      </div>
    </section>
  );
}
