"use client";

import { useState } from "react";
import { ApiError, createLesson } from "@/lib/api";
import type { CreateLessonInput, Lesson } from "@/types/api";
import { AgentTrace } from "./AgentTrace";
import { ErrorBanner } from "./ErrorBanner";
import { LessonForm } from "./LessonForm";
import { LessonView } from "./LessonView";
import { PipelineProgress } from "./PipelineProgress";

type PageState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; lesson: Lesson };

export function StudyPage() {
  const [state, setState] = useState<PageState>({ status: "idle" });
  const [lastInput, setLastInput] = useState<CreateLessonInput | null>(null);

  async function transform(input: CreateLessonInput) {
    setLastInput(input);
    setState({ status: "loading" });
    try {
      const lesson = await createLesson(input);
      setState({ status: "ready", lesson });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setState({ status: "error", message });
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-8 sm:px-6 sm:py-12">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">HumZehan</h1>
        <p className="mt-1 text-lg text-muted">Study the way your mind works.</p>
      </header>

      <section aria-label="Create a lesson" className="rounded-xl border border-border bg-surface p-5 sm:p-6">
        <LessonForm busy={state.status === "loading"} onSubmit={(input) => void transform(input)} />
      </section>

      {state.status === "loading" && <PipelineProgress />}

      {state.status === "error" && (
        <ErrorBanner
          message={state.message}
          onRetry={lastInput ? () => void transform(lastInput) : undefined}
        />
      )}

      {state.status === "ready" && (
        <>
          <AgentTrace trace={state.lesson.trace} />
          <LessonView key={state.lesson.lesson_id} lesson={state.lesson} />
        </>
      )}
    </main>
  );
}
