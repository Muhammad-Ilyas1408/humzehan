// Mixed Urdu/English text: keep English terms, numbers and formulas left-to-right inside
// right-to-left Urdu. Each Latin/number run is wrapped in invisible Unicode isolates
// (LRI … PDI), so "F = ma" never shows as "ma = F" and "9.8 m/s²" keeps its order.

export const LRI = "⁦";
export const PDI = "⁩";

// Start/end of a run: Latin letter, digit, superscript/subscript, degree or percent sign.
const EDGE = "A-Za-z0-9À-ɏ²³¹⁰-₟°%";
// Inside a run, also spaces and formula symbols (brackets stay outside, so they mirror in RTL).
const INNER = `${EDGE} .,:'’=+\\-−×÷*/^<>≈≤≥`;
const LTR_RUN = new RegExp(`[${EDGE}](?:[${INNER}]*[${EDGE}])?`, "g");

/** Wrap every left-to-right run (English words, numbers, formulas) in direction isolates. */
export function isolateLtr(text: string): string {
  return text.replace(LTR_RUN, (run) => `${LRI}${run}${PDI}`);
}

interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  children?: HastNode[];
}

function isolateTree(node: HastNode): void {
  if (node.type === "text" && typeof node.value === "string") {
    node.value = isolateLtr(node.value);
    return;
  }
  if (node.tagName === "code" || node.tagName === "pre") return;
  node.children?.forEach(isolateTree);
}

/** Rehype plugin for react-markdown: apply `isolateLtr` to every rendered text node.
 * Runs after Markdown parsing, so list numbers and other syntax are not affected. */
export function rehypeIsolateLtr() {
  return (tree: HastNode) => {
    isolateTree(tree);
  };
}
