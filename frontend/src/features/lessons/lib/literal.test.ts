import { describe, expect, it } from "vitest";
import { LITERAL_LABELS, literalSectionKind, splitLiteralSections } from "./literal";

describe("splitLiteralSections", () => {
  it("splits on bold-only lines", () => {
    const md = "**What it is**\nA plant makes food.\n\n**How it works:**\nIt uses light.\n**Example**\nA leaf.";
    expect(splitLiteralSections(md)).toEqual([
      { title: "What it is", kind: "what", body: "A plant makes food." },
      { title: "How it works", kind: "how", body: "It uses light." },
      { title: "Example", kind: "example", body: "A leaf." },
    ]);
  });

  it("splits an Urdu body on the Urdu labels", () => {
    const md =
      "**یہ کیا ہے**\nپودے خوراک بناتے ہیں۔\n\n**یہ کیسے کام کرتا ہے:**\nوہ روشنی (light) استعمال کرتے ہیں۔\n**مثال**\nپتا۔";
    expect(splitLiteralSections(md)).toEqual([
      { title: "یہ کیا ہے", kind: "what", body: "پودے خوراک بناتے ہیں۔" },
      { title: "یہ کیسے کام کرتا ہے", kind: "how", body: "وہ روشنی (light) استعمال کرتے ہیں۔" },
      { title: "مثال", kind: "example", body: "پتا۔" },
    ]);
  });

  it("handles the colon inside the bold text", () => {
    expect(splitLiteralSections("**مثال:**\nپتا۔\n**What it is:**\nA leaf.")).toEqual([
      { title: "مثال", kind: "example", body: "پتا۔" },
      { title: "What it is", kind: "what", body: "A leaf." },
    ]);
  });

  it("keeps other bold-only lines as sections without a kind", () => {
    expect(splitLiteralSections("**Note**\nBe careful.")).toEqual([
      { title: "Note", kind: null, body: "Be careful." },
    ]);
  });

  it("keeps text before the first section as an untitled section", () => {
    expect(splitLiteralSections("Intro.\n**What it is**\nBody.")).toEqual([
      { title: "", kind: null, body: "Intro." },
      { title: "What it is", kind: "what", body: "Body." },
    ]);
  });

  it("returns [] when there are no section lines", () => {
    expect(splitLiteralSections("Plain text with **bold** inside.")).toEqual([]);
    expect(splitLiteralSections("سادہ متن میں **اہم** لفظ۔")).toEqual([]);
  });
});

describe("literalSectionKind", () => {
  it("recognises every English and Urdu label", () => {
    for (const [kind, labels] of Object.entries(LITERAL_LABELS)) {
      expect(literalSectionKind(labels.en)).toBe(kind);
      expect(literalSectionKind(labels.ur)).toBe(kind);
    }
  });

  it("ignores case, extra spaces and a trailing colon", () => {
    expect(literalSectionKind("  how IT works: ")).toBe("how");
    expect(literalSectionKind("یہ  کیسے کام کرتا ہے：")).toBe("how");
  });

  it("returns null for other titles", () => {
    expect(literalSectionKind("Summary")).toBeNull();
    expect(literalSectionKind("خلاصہ")).toBeNull();
  });
});
