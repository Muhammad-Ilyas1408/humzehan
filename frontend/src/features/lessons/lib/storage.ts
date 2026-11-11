const NAME_KEY = "humzehan.studentName";

/** Read the remembered student name; storage may be blocked, so never throw. */
export function loadStudentName(): string {
  try {
    return window.localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveStudentName(name: string): void {
  try {
    window.localStorage.setItem(NAME_KEY, name);
  } catch {
    // Storage unavailable (private mode, blocked): the name just isn't remembered.
  }
}
