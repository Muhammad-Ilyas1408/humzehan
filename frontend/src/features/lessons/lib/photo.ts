/** Photo types the backend accepts (it checks the real file content as well). */
export const ACCEPTED_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;

/** Value for the file input's `accept` attribute. */
export const PHOTO_ACCEPT = ACCEPTED_PHOTO_TYPES.join(",");

export const WRONG_PHOTO_TYPE_MESSAGE = "Please choose a JPG, PNG or WEBP photo.";
export const EMPTY_PHOTO_MESSAGE = "This file is empty. Please choose another photo.";

function megabytes(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, "");
}

/** Check a chosen file before uploading it. Returns a message for the student, or null if OK. */
export function checkPhoto(file: { type: string; size: number }, maxBytes: number): string | null {
  if (!(ACCEPTED_PHOTO_TYPES as readonly string[]).includes(file.type.toLowerCase())) {
    return WRONG_PHOTO_TYPE_MESSAGE;
  }
  if (file.size === 0) {
    return EMPTY_PHOTO_MESSAGE;
  }
  if (file.size > maxBytes) {
    return `This photo is ${megabytes(file.size)} MB. The maximum is ${megabytes(maxBytes)} MB. Please choose a smaller photo.`;
  }
  return null;
}
