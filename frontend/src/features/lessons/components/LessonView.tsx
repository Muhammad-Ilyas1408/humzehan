"use client";

import { useState } from "react";
import type { Lesson } from "@/types/api";
import { modeLabel } from "../modes";
import { ChunkCard } from "./ChunkCard";

/** Remount with key={lesson.lesson_id} so tick boxes reset for a new lesson. */
export function LessonView({ lesson }: { lesson: Lesson }) {
  const [done, setDone] = useState<boolean[]>(() => lesson.chunks.map(() => false));
  const doneCount = done.filter(Boolean).length;
  const total = lesson.chunks.length;

  return (
    <section aria-labelledby="lesson-title" className={`mode-${lesson.mode} flex flex-col gap-5`}>
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-muted">
          {modeLabel(lesson.mode)} learning style
        </p>
        <h2 id="lesson-title" className="mt-1 text-2xl font-semibold sm:text-3xl">
          {lesson.title}
        </h2>
      </header>

      {lesson.mode === "focus" && total > 0 && (
        <div className="sticky top-0 z-10 rounded-xl border border-border bg-surface px-5 py-3">
          <label htmlFor="focus-progress" className="text-sm font-semibold">
            {doneCount} of {total} chunks done
          </label>
          <progress
            id="focus-progress"
            max={total}
            value={doneCount}
            className="mt-2 block h-3 w-full overflow-hidden rounded-full [&::-moz-progress-bar]:bg-accent [&::-webkit-progress-bar]:bg-accent-soft [&::-webkit-progress-value]:bg-accent"
          />
        </div>
      )}

      {lesson.chunks.map((chunk, i) => (
        <ChunkCard
          key={i}
          lessonId={lesson.lesson_id}
          mode={lesson.mode}
          chunk={chunk}
          index={i}
          done={done[i] ?? false}
          onDoneChange={(value) =>
            setDone((prev) => prev.map((d, j) => (j === i ? value : d)))
          }
        />
      ))}
    </section>
  );
}
