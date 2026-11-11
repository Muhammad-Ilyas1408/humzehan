import type { CreateLessonInput, Lesson, ProgressCreate } from "@/types/api";
import { API_URL } from "./config";

export const UNREACHABLE_MESSAGE =
  "We couldn't reach the HumZehan server. Check that it is running and try again.";

export class ApiError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Turn a backend error body ({"detail": ...}) into a message for the student. */
export function errorMessageFromBody(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    // FastAPI 422: a list of {loc, msg, type}.
    if (Array.isArray(detail) && detail.length > 0) {
      const first: unknown = detail[0];
      if (first && typeof first === "object" && "msg" in first) {
        const msg = (first as { msg: unknown }).msg;
        if (typeof msg === "string" && msg.trim()) {
          return msg;
        }
      }
    }
  }
  return `Something went wrong (error ${status}). Please try again.`;
}

async function request(path: string, init: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1${path}`, init);
  } catch {
    throw new ApiError(UNREACHABLE_MESSAGE, null);
  }
  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Not JSON: fall back to the generic message.
    }
    throw new ApiError(errorMessageFromBody(body, response.status), response.status);
  }
  return response;
}

/** POST /api/v1/lessons — returns when the agent has finished the lesson. */
export async function createLesson(input: CreateLessonInput): Promise<Lesson> {
  const form = new FormData();
  form.set("student", input.student);
  form.set("mode", input.mode);
  form.set("text", input.text);
  const response = await request("/lessons", { method: "POST", body: form });
  return (await response.json()) as Lesson;
}

/** POST /api/v1/progress — saves a quiz score (0–3) for one chunk. */
export async function recordProgress(progress: ProgressCreate): Promise<void> {
  await request("/progress", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(progress),
  });
}
