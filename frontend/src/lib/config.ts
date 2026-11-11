/** Backend base URL, inlined at build time. */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

/** Must match the backend's MAX_SOURCE_CHARS. */
export const MAX_SOURCE_CHARS = 8000;
