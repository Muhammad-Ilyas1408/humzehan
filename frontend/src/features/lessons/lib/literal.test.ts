import { describe, expect, it } from "vitest";
import { splitLiteralSections } from "./literal";

describe("splitLiteralSections", () => {
  it("splits on bold-only lines", () => {
    const md = "**What it is**\nA plant makes food.\n\n**How it works:**\nIt uses light.\n**Example**\nA leaf.";
    expect(splitLiteralSections(md)).toEqual([
      { title: "What it is", body: "A plant makes food." },
      { title: "How it works", body: "It uses light." },
      { title: "Example", body: "A leaf." },
    ]);
  });

  it("keeps text before the first section as an untitled section", () => {
    expect(splitLiteralSections("Intro.\n**What it is**\nBody.")).toEqual([
      { title: "", body: "Intro." },
      { title: "What it is", body: "Body." },
    ]);
  });

  it("returns [] when there are no section lines", () => {
    expect(splitLiteralSections("Plain text with **bold** inside.")).toEqual([]);
  });
});
