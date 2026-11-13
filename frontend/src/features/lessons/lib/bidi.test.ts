import { describe, expect, it } from "vitest";
import { LRI, PDI, isolateLtr, rehypeIsolateLtr } from "./bidi";

const iso = (s: string) => `${LRI}${s}${PDI}`;

describe("isolateLtr", () => {
  it("keeps a formula together as one left-to-right run", () => {
    expect(isolateLtr("قانون F = ma ہے")).toBe(`قانون ${iso("F = ma")} ہے`);
  });

  it("isolates an English term but leaves its brackets in the Urdu text", () => {
    expect(isolateLtr("بخارات بننا (evaporation)")).toBe(`بخارات بننا (${iso("evaporation")})`);
  });

  it("isolates numbers, units and decimals", () => {
    expect(isolateLtr("سال 1687 میں")).toBe(`سال ${iso("1687")} میں`);
    expect(isolateLtr("رفتار 9.8 m/s² ہے")).toBe(`رفتار ${iso("9.8 m/s²")} ہے`);
  });

  it("does not swallow surrounding spaces or Urdu punctuation", () => {
    expect(isolateLtr("پانی (water)، ہوا (air)۔")).toBe(`پانی (${iso("water")})، ہوا (${iso("air")})۔`);
  });

  it("leaves Urdu-only text unchanged", () => {
    expect(isolateLtr("پودے اپنی خوراک بناتے ہیں۔")).toBe("پودے اپنی خوراک بناتے ہیں۔");
  });
});

describe("rehypeIsolateLtr", () => {
  it("isolates text nodes but not code", () => {
    const tree = {
      type: "root",
      children: [
        { type: "element", tagName: "p", children: [{ type: "text", value: "F = ma ہے" }] },
        { type: "element", tagName: "code", children: [{ type: "text", value: "x = 1" }] },
      ],
    };
    rehypeIsolateLtr()(tree);
    expect(tree.children[0].children[0].value).toBe(`${iso("F = ma")} ہے`);
    expect(tree.children[1].children[0].value).toBe("x = 1");
  });
});
