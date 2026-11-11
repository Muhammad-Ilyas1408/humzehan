"use client";

import { useId } from "react";
import type { Chunk, LearningMode } from "@/types/api";
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
}

export function ChunkCard({ lessonId, mode, chunk, index, done, onDoneChange }: ChunkCardProps) {
  const id = useId();
  const headingId = `${id}-heading`;
  const showGlossary = chunk.glossary.length > 0;

  return (
    <article
      aria-labelledby={headingId}
      className="chunk-card rounded-xl border border-border bg-surface p-5 sm:p-6"
    >
      {mode === "focus" && chunk.hook && (
        <p className="mb-4 rounded-lg border-l-4 border-accent bg-accent-soft px-4 py-3">
          <span className="font-semibold">Key idea: </span>
          {chunk.hook}
        </p>
      )}

      <h3 id={headingId} className="text-xl font-semibold">
        <span className="text-muted">{index + 1}. </span>
        {chunk.heading}
      </h3>

      <div className="mt-3">
        {mode === "literal" ? <LiteralBody body={chunk.body} /> : <Markdown>{chunk.body}</Markdown>}
      </div>

      {showGlossary && (
        <section aria-label="Glossary" className="mt-5 rounded-lg border border-border bg-surface/70 p-4">
          <h4 className="font-semibold">Glossary</h4>
          <dl className="mt-2 flex flex-col gap-2">
            {chunk.glossary.map((item) => (
              <div key={item.term}>
                <dt className="inline font-semibold">{item.term}: </dt>
                <dd className="inline">{item.meaning}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      <ChunkQuiz lessonId={lessonId} chunkIndex={index} quiz={chunk.quiz} />

      {mode === "focus" && (
        <label className="mt-6 flex min-h-12 cursor-pointer items-center gap-3 rounded-lg border border-border px-4 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent">
          <input
            type="checkbox"
            checked={done}
            onChange={(e) => onDoneChange(e.target.checked)}
            className="h-5 w-5 accent-accent focus-visible:outline-none"
          />
          <span className="font-semibold">I’ve finished this chunk</span>
        </label>
      )}
    </article>
  );
}

function LiteralBody({ body }: { body: string }) {
  const sections = splitLiteralSections(body);
  if (sections.length === 0) return <Markdown>{body}</Markdown>;
  return (
    <div className="flex flex-col gap-4">
      {sections.map((section, i) => (
        <section key={i}>
          {section.title && (
            <h4 className="mb-1 text-sm font-bold uppercase tracking-wide text-accent-strong">
              {section.title}
            </h4>
          )}
          <Markdown>{section.body}</Markdown>
        </section>
      ))}
    </div>
  );
}
