import ReactMarkdown from "react-markdown";

/** Renders lesson Markdown. Raw HTML in the text is not rendered (react-markdown default). */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-lesson">
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  );
}
