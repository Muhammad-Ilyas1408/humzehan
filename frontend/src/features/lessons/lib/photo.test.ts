import { describe, expect, it } from "vitest";
import {
  EMPTY_PHOTO_MESSAGE,
  PHOTO_ACCEPT,
  WRONG_PHOTO_TYPE_MESSAGE,
  checkPhoto,
} from "./photo";

const MB = 1024 * 1024;
const MAX = 10 * MB;

describe("checkPhoto", () => {
  it.each(["image/jpeg", "image/png", "image/webp", "IMAGE/JPEG"])("accepts %s", (type) => {
    expect(checkPhoto({ type, size: 2 * MB }, MAX)).toBeNull();
  });

  it.each(["image/heic", "image/gif", "application/pdf", "text/plain", ""])(
    "rejects type %j",
    (type) => {
      expect(checkPhoto({ type, size: 2 * MB }, MAX)).toBe(WRONG_PHOTO_TYPE_MESSAGE);
    },
  );

  it("rejects an empty file", () => {
    expect(checkPhoto({ type: "image/png", size: 0 }, MAX)).toBe(EMPTY_PHOTO_MESSAGE);
  });

  it("accepts a photo exactly at the limit", () => {
    expect(checkPhoto({ type: "image/png", size: MAX }, MAX)).toBeNull();
  });

  it("rejects a photo over the limit and says the sizes", () => {
    const message = checkPhoto({ type: "image/jpeg", size: 12.5 * MB }, MAX);
    expect(message).toContain("12.5 MB");
    expect(message).toContain("maximum is 10 MB");
  });

  it("checks the type before the size", () => {
    expect(checkPhoto({ type: "image/gif", size: 0 }, MAX)).toBe(WRONG_PHOTO_TYPE_MESSAGE);
  });
});

describe("PHOTO_ACCEPT", () => {
  it("lists exactly the three accepted types", () => {
    expect(PHOTO_ACCEPT).toBe("image/jpeg,image/png,image/webp");
  });
});
