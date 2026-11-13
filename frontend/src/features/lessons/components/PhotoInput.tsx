"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ApiError, extractText } from "@/lib/api";
import { MAX_IMAGE_BYTES } from "@/lib/config";
import { PHOTO_ACCEPT, checkPhoto } from "../lib/photo";

const TIPS = [
  "One page per photo",
  "Good light",
  "Page flat, photo taken from straight above",
  "No shadows or fingers over the text",
];

interface PhotoInputProps {
  /** True while a lesson is being created: nothing can be changed. */
  disabled: boolean;
  /** Called with the text read from the photo. */
  onText: (text: string) => void;
  /** Called when reading starts (true) and ends (false). */
  onReadingChange: (reading: boolean) => void;
}

export function PhotoInput({ disabled, onText, onReadingChange }: PhotoInputProps) {
  const id = useId();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  // Latest preview URL, so it can be released when the component unmounts.
  const previewRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  function replacePreview(next: File | null) {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const url = next ? URL.createObjectURL(next) : null;
    previewRef.current = url;
    setPreviewUrl(url);
  }

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0] ?? null;
    if (!chosen) return; // picker cancelled: keep the current photo
    const problem = checkPhoto(chosen, MAX_IMAGE_BYTES);
    setError(problem);
    if (problem) {
      setFile(null);
      replacePreview(null);
      event.target.value = ""; // allow choosing the same file again after fixing it
      return;
    }
    setFile(chosen);
    replacePreview(chosen);
  }

  async function readPhoto() {
    if (!file || reading) return;
    setError(null);
    setReading(true);
    onReadingChange(true);
    try {
      onText(await extractText(file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setReading(false);
      onReadingChange(false);
    }
  }

  const inputId = `${id}-photo`;
  const tipsId = `${id}-tips`;
  const errorId = `${id}-error`;
  const locked = disabled || reading;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <label htmlFor={inputId} className="text-base font-semibold">
          Photo of a textbook page
        </label>
        <div id={tipsId} className="rounded-lg bg-accent-soft p-4 text-sm">
          <p className="font-semibold">For the best result:</p>
          <ul className="mt-1 list-disc pl-5">
            {TIPS.map((tip) => (
              <li key={tip}>{tip}</li>
            ))}
          </ul>
          <p className="mt-2 text-muted">JPG, PNG or WEBP, up to 10 MB.</p>
        </div>
        {/* No `capture` attribute: phones offer both the camera and the photo library. */}
        <input
          id={inputId}
          type="file"
          accept={PHOTO_ACCEPT}
          onChange={handleChange}
          disabled={locked}
          aria-describedby={error ? `${tipsId} ${errorId}` : tipsId}
          aria-invalid={error !== null}
          className="min-h-12 rounded-lg border border-border bg-surface p-2 text-base file:mr-3 file:min-h-10 file:rounded-md file:border-0 file:bg-accent-soft file:px-4 file:font-semibold disabled:opacity-60"
        />
      </div>

      {previewUrl && (
        // A local blob: URL, so next/image optimisation does not apply.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={previewUrl}
          alt="Preview of the chosen photo"
          className="max-h-80 w-auto self-start rounded-lg border border-border object-contain"
        />
      )}

      {error && (
        <p id={errorId} role="alert" className="rounded-lg border border-danger bg-danger-soft p-3 text-danger">
          {error}
        </p>
      )}

      {reading ? (
        <div role="status" aria-live="polite" className="flex items-center gap-3">
          <span aria-hidden="true" className="calm-pulse h-3 w-3 rounded-full bg-accent" />
          <span className="font-semibold">Reading your photo…</span>
        </div>
      ) : (
        <div>
          <button
            type="button"
            onClick={() => void readPhoto()}
            disabled={!file || locked}
            className="min-h-12 w-full rounded-lg border-2 border-accent bg-surface px-6 text-lg font-semibold text-accent-strong disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            Read text from photo
          </button>
        </div>
      )}
    </div>
  );
}
