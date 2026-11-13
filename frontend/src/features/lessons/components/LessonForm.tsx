"use client";

import { useId, useState, useSyncExternalStore } from "react";
import { MAX_SOURCE_CHARS } from "@/lib/config";
import type { CreateLessonInput, LearningMode } from "@/types/api";
import { LEARNING_MODES } from "../modes";
import { loadStudentName, saveStudentName } from "../lib/storage";
import { charCountState } from "../lib/text";
import { PhotoInput } from "./PhotoInput";

type Source = "text" | "photo";

const SOURCES: { value: Source; label: string }[] = [
  { value: "text", label: "Paste text" },
  { value: "photo", label: "Upload a photo" },
];

const noopSubscribe = () => () => {};

interface LessonFormProps {
  busy: boolean;
  onSubmit: (input: CreateLessonInput) => void;
}

export function LessonForm({ busy, onSubmit }: LessonFormProps) {
  const id = useId();
  // The remembered name comes from localStorage on the client only ("" on the server).
  const storedName = useSyncExternalStore(noopSubscribe, loadStudentName, () => "");
  const [editedName, setEditedName] = useState<string | null>(null);
  const name = editedName ?? storedName;
  const [text, setText] = useState("");
  const [mode, setMode] = useState<LearningMode>("focus");
  const [source, setSource] = useState<Source>("text");
  const [readingPhoto, setReadingPhoto] = useState(false);
  const [fromPhoto, setFromPhoto] = useState(false);

  const chars = charCountState(text, MAX_SOURCE_CHARS);
  const nameMissing = name.trim().length === 0;
  const canSubmit =
    !busy && !readingPhoto && source === "text" && !nameMissing && !chars.empty && !chars.over;

  const nameId = `${id}-name`;
  const textId = `${id}-text`;
  const hintId = `${id}-hint`;
  const counterId = `${id}-counter`;
  const photoNoteId = `${id}-photo-note`;

  function handlePhotoText(extracted: string) {
    setText(extracted);
    setFromPhoto(true);
    setSource("text");
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    const student = name.trim();
    saveStudentName(student);
    onSubmit({ student, mode, text });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6" aria-busy={busy}>
      <div className="flex flex-col gap-2">
        <label htmlFor={nameId} className="text-base font-semibold">
          Your name
        </label>
        <input
          id={nameId}
          type="text"
          autoComplete="given-name"
          value={name}
          onChange={(e) => setEditedName(e.target.value)}
          disabled={busy}
          maxLength={100}
          className="min-h-12 rounded-lg border border-border bg-surface px-4 text-base disabled:opacity-60"
        />
      </div>

      <fieldset className="flex flex-col gap-3" disabled={busy || readingPhoto}>
        <legend className="mb-1 text-base font-semibold">Study text from</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {SOURCES.map((s) => {
            const selected = source === s.value;
            return (
              <label
                key={s.value}
                className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border-2 px-4 py-3 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${
                  selected ? "border-accent bg-accent-soft" : "border-border bg-surface"
                }`}
              >
                <input
                  type="radio"
                  name={`${id}-source`}
                  value={s.value}
                  checked={selected}
                  onChange={() => setSource(s.value)}
                  className="h-5 w-5 accent-accent focus-visible:outline-none"
                />
                <span className="text-lg font-semibold">{s.label}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      {/* Both panels stay mounted, so the chosen photo is kept when switching views. */}
      <div hidden={source !== "photo"}>
        <PhotoInput
          disabled={busy}
          onText={handlePhotoText}
          onReadingChange={setReadingPhoto}
        />
      </div>

      <div className="flex flex-col gap-2" hidden={source !== "text"}>
        <label htmlFor={textId} className="text-base font-semibold">
          Study text
        </label>
        <p id={hintId} className="text-sm text-muted">
          Paste a page or section from your textbook.
        </p>
        {fromPhoto && (
          <p
            id={photoNoteId}
            className="rounded-lg border border-accent bg-accent-soft p-3 text-base font-semibold"
          >
            Check the text below and fix any mistakes before you transform.
          </p>
        )}
        <textarea
          id={textId}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            if (!e.target.value.trim()) setFromPhoto(false);
          }}
          disabled={busy}
          rows={12}
          aria-describedby={`${hintId} ${fromPhoto ? `${photoNoteId} ` : ""}${counterId}`}
          aria-invalid={chars.over}
          className={`rounded-lg border bg-surface p-4 text-base leading-relaxed disabled:opacity-60 ${
            chars.over ? "border-danger" : "border-border"
          }`}
        />
        <p
          id={counterId}
          className={`text-sm ${chars.over ? "font-semibold text-danger" : "text-muted"}`}
        >
          {chars.count.toLocaleString("en-US")} / {MAX_SOURCE_CHARS.toLocaleString("en-US")}{" "}
          characters
          {chars.over &&
            ` — please remove ${(-chars.remaining).toLocaleString("en-US")} characters.`}
        </p>
      </div>

      <fieldset className="flex flex-col gap-3" disabled={busy}>
        <legend className="mb-1 text-base font-semibold">Choose your learning style</legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {LEARNING_MODES.map((m) => {
            const selected = mode === m.value;
            return (
              <label
                key={m.value}
                className={`flex cursor-pointer flex-col gap-1 rounded-xl border-2 p-4 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${
                  selected ? "border-accent bg-accent-soft" : "border-border bg-surface"
                }`}
              >
                <span className="flex items-center gap-3">
                  <input
                    type="radio"
                    name={`${id}-mode`}
                    value={m.value}
                    checked={selected}
                    onChange={() => setMode(m.value)}
                    className="h-5 w-5 accent-accent focus-visible:outline-none"
                  />
                  <span className="text-lg font-semibold">{m.label}</span>
                </span>
                <span className="text-sm text-muted">{m.description}</span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div>
        <button
          type="submit"
          disabled={!canSubmit}
          className="min-h-12 w-full rounded-lg bg-accent px-6 text-lg font-semibold text-white hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {busy ? "Transforming…" : "Transform"}
        </button>
        {nameMissing && !busy && (
          <p className="mt-2 text-sm text-muted">Enter your name to continue.</p>
        )}
        {source === "photo" && !busy && (
          <p className="mt-2 text-sm text-muted">
            Read the text from your photo first. You can check it before you transform.
          </p>
        )}
      </div>
    </form>
  );
}
