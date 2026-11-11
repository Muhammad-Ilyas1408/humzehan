import { describe, expect, it } from "vitest";
import { errorMessageFromBody } from "./api";

describe("errorMessageFromBody", () => {
  it("returns a string detail as is", () => {
    expect(errorMessageFromBody({ detail: "Text is too long." }, 400)).toBe("Text is too long.");
  });

  it("returns the first message of a 422 error list", () => {
    const body = { detail: [{ loc: ["body", "mode"], msg: "Input should be 'focus'", type: "enum" }] };
    expect(errorMessageFromBody(body, 422)).toBe("Input should be 'focus'");
  });

  it("falls back to a generic message", () => {
    expect(errorMessageFromBody(null, 500)).toContain("error 500");
    expect(errorMessageFromBody({ other: 1 }, 502)).toContain("error 502");
  });
});
