/** Backend base URL, inlined at build time. */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

/** Must match the backend's MAX_SOURCE_CHARS. */
export const MAX_SOURCE_CHARS = 8000;

/** Must match the backend's MAX_IMAGE_BYTES (10 MB). */
export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
