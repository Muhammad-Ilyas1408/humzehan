"use client";

import { useEffect, useState } from "react";

// The agent's pipeline. The API answers only when the lesson is finished, so these steps
// describe what the agent does: no step is marked done and no checker decision is shown.
const STEPS = [
  "Reading your text",
  "Writing chunks in your learning style",
  "Writing quiz questions",
  "Checking the lesson against your text",
];

export function PipelineProgress() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <section
      role="status"
      aria-live="polite"
      aria-label="Creating your lesson"
      className="rounded-xl border border-border bg-surface p-6"
    >
      <div className="flex items-center gap-3">
        <span aria-hidden="true" className="calm-pulse h-3 w-3 rounded-full bg-accent" />
        <h2 className="text-lg font-semibold">Creating your lesson…</h2>
      </div>
      <p className="mt-2 text-muted">
        This usually takes under 30 seconds. The agent works through these steps:
      </p>
      <ol className="mt-4 flex flex-col gap-2">
        {STEPS.map((step, i) => (
          <li key={step} className="flex items-center gap-3">
            <span
              aria-hidden="true"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border text-sm text-muted"
            >
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      {/* Visual only: a live counter would be announced every second. */}
      <p aria-hidden="true" className="mt-4 text-sm text-muted">
        {seconds} s
      </p>
    </section>
  );
}
