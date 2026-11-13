import { afterEach, describe, expect, it, vi } from "vitest";
import { createLesson, errorMessageFromBody } from "./api";

describe("createLesson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([true, false])("sends the urdu field (%s) with the form", async (urdu) => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ lesson_id: "l1" }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    await createLesson({ student: "Ali", mode: "focus", text: "Plants make food.", urdu });

    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    const form = init.body as FormData;
    expect(form.get("urdu")).toBe(String(urdu));
    expect(form.get("mode")).toBe("focus");
  });
});

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
