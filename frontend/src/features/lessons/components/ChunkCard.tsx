"use client";

import { useId } from "react";
import type { Chunk, LearningMode } from "@/types/api";
import { isolateLtr } from "../lib/bidi";
import type { LessonLabels, LessonLang } from "../lib/labels";
import { splitLiteralSections } from "../lib/literal";
import { ChunkQuiz } from "./ChunkQuiz";
import { Markdown } from "./Markdown";

interface ChunkCardProps {
  lessonId: string;
  mode: LearningMode;
  chunk: Chunk;
  index: number;
  done: boolean;
  onDoneChange: (done: boolean) => void;
  lang: LessonLang;
  labels: LessonLabels;
}

export function ChunkCard({
  lessonId,
  mode,
  chunk,
  index,
  done,
  onDoneChange,
  lang,
  labels,
}: ChunkCardProps) {
  const id = useId();
  const headingId = `${id}-heading`;
  const showGlossary = chunk.glossary.length > 0;
  const urdu = lang === "ur";
  const text = urdu ? isolateLtr : (s: string) => s;

  return (
    <article
      aria-labelledby={headingId}
      className="chunk-card rounded-xl border border-border bg-surface p-5 sm:p-6"
    >
      {mode === "focus" && chunk.hook && (
        <p className="mb-4 rounded-lg border-s-4 border-accent bg-accent-soft px-4 py-3">
          <span className="font-semibold">{labels.keyIdea}: </span>
          {text(chunk.hook)}
        </p>
      )}

      <h3 id={headingId} className="text-xl font-semibold">
        <span className="text-muted">{index + 1}. </span>
        {text(chunk.heading)}
      </h3>

      <div className="mt-3">
        {mode === "literal" ? (
          <LiteralBody body={chunk.body} isolate={urdu} />
        ) : (
          <Markdown isolate={urdu}>{chunk.body}</Markdown>
        )}
      </div>

      {showGlossary && (
        <section aria-label={labels.glossary} className="mt-5 rounded-lg border border-border bg-surface/70 p-4">
          <h4 className="font-semibold">{labels.glossary}</h4>
          <dl className="mt-2 flex flex-col gap-2">
            {chunk.glossary.map((item, gi) => (
              <div key={gi}>
                <dt className="inline font-semibold">{text(item.term)}: </dt>
                <dd className="inline">{text(item.meaning)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <ChunkQuiz lessonId={lessonId} chunkIndex={index} quiz={chunk.quiz} lang={lang} labels={labels} />

      {mode === "focus" && (
        <label className="mt-6 flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-border px-4 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent">
          <input
            type="checkbox"
            checked={done}
            onChange={(e) => onDoneChange(e.target.checked)}
            className="h-5 w-5 accent-accent focus-visible:outline-none"
          />
          <span className="font-semibold">{labels.chunkDone}</span>
        </label>
      )}
    </article>
  );
}

function LiteralBody({ body, isolate }: { body: string; isolate: boolean }) {
  const sections = splitLiteralSections(body);
  if (sections.length === 0) return <Markdown isolate={isolate}>{body}</Markdown>;
  return (
    <div className="flex flex-col gap-4">
      {sections.map((section, i) => (
        <section key={i}>
          {section.title && (
            <h4 className="mb-1 text-sm font-bold uppercase tracking-wide text-accent-strong">
              {isolate ? isolateLtr(section.title) : section.title}
            </h4>
          )}
          <Markdown isolate={isolate}>{section.body}</Markdown>
        </section>
      ))}
    </div>
  );
}
