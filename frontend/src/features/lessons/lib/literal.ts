export type LiteralSectionKind = "what" | "how" | "example";

export interface LiteralSection {
  title: string;
  /** Which Literal section the title names (English or Urdu label), or null for other titles. */
  kind: LiteralSectionKind | null;
  /** Markdown under the title. */
  body: string;
}

/** The fixed Literal section labels, in English and in simple Urdu (F5). */
export const LITERAL_LABELS: Record<LiteralSectionKind, { en: string; ur: string }> = {
  what: { en: "What it is", ur: "یہ کیا ہے" },
  how: { en: "How it works", ur: "یہ کیسے کام کرتا ہے" },
  example: { en: "Example", ur: "مثال" },
};

// A line that is only bold text, e.g. "**What it is**", "**How it works:**" or "**یہ کیا ہے**".
const SECTION_LINE = /^\s*\*\*([^*]+?)\*\*\s*[:：]?\s*$/;

const normalise = (title: string) =>
  title.trim().replace(/[:：]$/, "").replace(/\s+/g, " ").trim().toLowerCase();

/** The section a title names, in English or Urdu ("How it works:" → "how"), else null. */
export function literalSectionKind(title: string): LiteralSectionKind | null {
  const wanted = normalise(title);
  for (const [kind, labels] of Object.entries(LITERAL_LABELS) as [
    LiteralSectionKind,
    { en: string; ur: string },
  ][]) {
    if (wanted === normalise(labels.en) || wanted === normalise(labels.ur)) return kind;
  }
  return null;
}

/**
 * Split a Literal chunk body into its "What it is / How it works / Example" sections
 * (or the Urdu "یہ کیا ہے / یہ کیسے کام کرتا ہے / مثال"). Splits on every bold-only line.
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
      sections.push({
        title: current.title,
        kind: current.title ? literalSectionKind(current.title) : null,
        body,
      });
    }
  };

  for (const line of markdown.split(/\r?\n/)) {
    const match = SECTION_LINE.exec(line);
    if (match) {
      found = true;
      flush();
      current = { title: match[1].trim().replace(/[:：]$/, "").trim(), lines: [] };
    } else {
      current.lines.push(line);
    }
  }
  flush();
  return found ? sections : [];
}
