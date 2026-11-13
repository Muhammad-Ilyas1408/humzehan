import ReactMarkdown from "react-markdown";
import { rehypeIsolateLtr } from "../lib/bidi";

const ISOLATE_PLUGINS = [rehypeIsolateLtr];

/** Renders lesson Markdown. Raw HTML in the text is not rendered (react-markdown default).
 * `isolate` (Urdu lessons) keeps English terms, numbers and formulas left-to-right. */
export function Markdown({ children, isolate = false }: { children: string; isolate?: boolean }) {
  return (
    <div className="prose-lesson">
      <ReactMarkdown rehypePlugins={isolate ? ISOLATE_PLUGINS : undefined}>{children}</ReactMarkdown>
    </div>
  );
}
