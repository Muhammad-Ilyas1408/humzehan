import type { TraceStep } from "@/types/api";

function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

/** The real trace returned by the API: every agent step, collapsed by default. */
export function AgentTrace({ trace }: { trace: TraceStep[] }) {
  const total = trace.reduce((sum, step) => sum + step.ms, 0);
  return (
    <details className="group rounded-xl border border-border bg-surface">
      <summary className="flex min-h-12 cursor-pointer items-center justify-between gap-3 rounded-xl px-5 py-3">
        <span className="font-semibold">
          Agent trace{" "}
          <span className="font-normal text-muted">
            ({trace.length} steps, {formatMs(total)} total)
          </span>
        </span>
        <span aria-hidden="true" className="text-muted group-open:rotate-180">
          ▾
        </span>
      </summary>
      <ol className="flex flex-col gap-3 border-t border-border px-5 py-4">
        {trace.map((step, i) => (
          <li key={i} className="flex flex-col gap-0.5 sm:flex-row sm:gap-4">
            <span className="flex shrink-0 gap-3 sm:w-48">
              <span className="font-mono text-sm font-semibold">{step.node}</span>
              <span className="font-mono text-sm text-muted">{formatMs(step.ms)}</span>
            </span>
            <span className="text-sm">{step.note}</span>
          </li>
        ))}
      </ol>
    </details>
  );
}
