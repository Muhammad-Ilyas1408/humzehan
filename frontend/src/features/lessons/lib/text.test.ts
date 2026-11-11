import { describe, expect, it } from "vitest";
import { charCountState } from "./text";

describe("charCountState", () => {
  it("marks empty and whitespace-only text as empty", () => {
    expect(charCountState("", 10).empty).toBe(true);
    expect(charCountState("   \n\t", 10).empty).toBe(true);
    expect(charCountState(" a ", 10).empty).toBe(false);
  });

  it("allows text exactly at the limit", () => {
    const state = charCountState("x".repeat(10), 10);
    expect(state).toEqual({ count: 10, remaining: 0, over: false, empty: false });
  });

  it("flags text over the limit", () => {
    const state = charCountState("x".repeat(11), 10);
    expect(state.over).toBe(true);
    expect(state.remaining).toBe(-1);
  });
});
