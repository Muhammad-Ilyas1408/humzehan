export interface LiteralSection {
  title: string;
  /** Markdown under the title. */
  body: string;
}

// A line that is only bold text, e.g. "**What it is**" or "**How it works:**".
const SECTION_LINE = /^\s*\*\*([^*]+?)\*\*\s*:?\s*$/;

/**
 * Split a Literal chunk body into its "What it is / How it works / Example" sections.
 * Returns [] when the body has no bold-only lines, so the caller renders it as-is.
 * Text before the first section line is kept as an untitled section.
 */
export function splitLiteralSections(markdown: string): LiteralSection[] {
  const sections: LiteralSection[] = [];
  let current: { title: string; lines: string[] } = { title: "", lines: [] };
  let found = false;

  const flush = () => {
    const body = current.lines.join("\n").trim();
    if (current.title || body) {
      sections.push({ title: current.title, body });
    }
  };

  for (const line of markdown.split(/\r?\n/)) {
    const match = SECTION_LINE.exec(line);
    if (match) {
      found = true;
      flush();
      current = { title: match[1].trim().replace(/:$/, ""), lines: [] };
    } else {
      current.lines.push(line);
    }
  }
  flush();
  return found ? sections : [];
}
