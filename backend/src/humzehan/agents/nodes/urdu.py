"""Urdu node (F5): translate the approved English lesson into simple Urdu.

Runs after the checker, because the checker and the grounding pre-check compare chunks with the
English SOURCE and cannot verify Urdu. Every chunk is translated in one parallel batch; each
translation is validated in code (same structure, same answer_index). Failed chunks are retried
once; if any chunk (or the title) still fails, the lesson stays in English with a trace note.
A lighter check asks that every bold key term of the English chunk appears in English in the
Urdu (in brackets): a chunk missing one is retried once and then accepted either way.
"""

import re

from langchain_core.language_models import BaseChatModel

from humzehan.agents.nodes._common import Node, add_step, ask_many_or_errors, start_timer
from humzehan.agents.prompts import load_prompt, prompt_section
from humzehan.agents.state import AgentState, ChunkTranslation, TitleTranslation
from humzehan.schemas.lesson import Chunk, EnglishVersion, LearningMode

STYLE_SECTIONS: dict[LearningMode, str] = {
    LearningMode.FOCUS: "Focus style",
    LearningMode.EASYREAD: "Easy-read style",
    LearningMode.LITERAL: "Literal style",
}


def validate_translation(english: Chunk, urdu: ChunkTranslation) -> list[str]:
    """Problems that make ``urdu`` an unfaithful copy of ``english``'s structure ([] = valid)."""
    problems: list[str] = []
    texts = [urdu.heading, urdu.body]
    if (english.hook is None) != (urdu.hook is None):
        problems.append("hook added" if english.hook is None else "hook missing")
    elif urdu.hook is not None:
        texts.append(urdu.hook)
    if len(urdu.glossary) != len(english.glossary):
        problems.append(
            f"glossary has {len(urdu.glossary)} items, expected {len(english.glossary)}"
        )
    else:
        texts += [text for item in urdu.glossary for text in (item.term, item.meaning)]
    if len(urdu.quiz) != len(english.quiz):
        problems.append(f"quiz has {len(urdu.quiz)} questions, expected {len(english.quiz)}")
    else:
        for number, (en_q, ur_q) in enumerate(zip(english.quiz, urdu.quiz, strict=True), 1):
            if len(ur_q.options) != len(en_q.options):
                problems.append(f"question {number} has {len(ur_q.options)} options")
            if ur_q.answer_index != en_q.answer_index:
                problems.append(f"question {number}: answer_index changed")
            texts += [ur_q.question, *ur_q.options]
    if any(not text.strip() for text in texts):
        problems.append("empty text")
    return problems


_BOLD = re.compile(r"\*\*([^*\n]+?)\*\*")
_BOLD_ONLY_LINE = re.compile(r"^\s*\*\*[^*\n]+?\*\*\s*:?\s*$")  # Literal section labels
_LATIN = re.compile(r"[A-Za-z]")


def _normalise(text: str) -> str:
    return " ".join(text.replace("*", "").lower().split())


def key_terms(chunk: Chunk) -> list[str]:
    """The bold key terms of an English chunk (body and hook), in order, without duplicates.
    Bold-only lines (Literal section labels such as **What it is**) are not key terms."""
    terms: dict[str, str] = {}
    for text in (chunk.hook or "", chunk.body):
        for line in text.splitlines():
            if _BOLD_ONLY_LINE.match(line):
                continue
            for match in _BOLD.finditer(line):
                term = " ".join(match.group(1).strip(" :.,;").split())
                if _LATIN.search(term):
                    terms.setdefault(term.lower(), term)
    return list(terms.values())


def missing_terms(terms: list[str], urdu: ChunkTranslation) -> list[str]:
    """The English ``terms`` that appear nowhere in the Urdu chunk (case-insensitive; a plural
    term also matches its singular, e.g. "forces" ~ "(force)")."""
    texts = [urdu.heading, urdu.body, urdu.hook or ""]
    texts += [text for item in urdu.glossary for text in (item.term, item.meaning)]
    haystack = _normalise(" ".join(texts))

    def found(term: str) -> bool:
        wanted = _normalise(term)
        variants = {wanted}
        if wanted.endswith("es"):
            variants.add(wanted[:-2])
        if wanted.endswith("s"):
            variants.add(wanted[:-1])
        return any(v and v in haystack for v in variants)

    return [term for term in terms if not found(term)]


def _chunk_prompt(
    chunk: Chunk, style: str, terms: list[str], missed: list[str] | None = None
) -> str:
    english = chunk.model_dump_json(
        include={"heading", "body", "hook", "glossary", "quiz"}, indent=2
    )
    parts = [style]
    if terms:
        parts.append(
            "KEY TERMS (the first time each appears, write the Urdu followed by the English "
            f"term in brackets): {', '.join(terms)}"
        )
    if missed:
        parts.append(
            "Your previous translation left out the English for: "
            f"{', '.join(missed)}. Add each in brackets after its Urdu word."
        )
    parts.append(f"ENGLISH CHUNK (JSON):\n{english}")
    parts.append("Translate this chunk into simple Urdu.")
    return "\n\n".join(parts)


def _title_prompt(title: str, style: str) -> str:
    return f"{style}\n\nENGLISH LESSON TITLE:\n{title}\n\nTranslate only this title."


def _check(english: Chunk, result: ChunkTranslation | Exception) -> list[str]:
    if isinstance(result, Exception):
        return [f"invalid output ({type(result).__name__})"]
    return validate_translation(english, result)


def make_urdu_node(llm: BaseChatModel) -> Node:
    system = load_prompt("urdu")

    def urdu(state: AgentState) -> AgentState:
        started = start_timer()
        chunks = state["chunks"]
        title = state["title"]
        style = prompt_section("urdu_styles", STYLE_SECTIONS[LearningMode(state["mode"])])
        terms = [key_terms(chunk) for chunk in chunks]
        prompts = [_chunk_prompt(chunk, style, terms[i]) for i, chunk in enumerate(chunks)]

        results = ask_many_or_errors(llm, ChunkTranslation, system, prompts)
        # Hard problems (structure) -> retry, then English fallback.
        problems = [_check(chunks[i], r) for i, r in enumerate(results)]
        # Soft problem (bold key terms missing in English) -> retry, then accept.
        missing = [
            missing_terms(terms[i], r)
            if isinstance(r, ChunkTranslation) and not problems[i]
            else []
            for i, r in enumerate(results)
        ]
        to_retry = [i for i in range(len(chunks)) if problems[i] or missing[i]]
        if to_retry:
            retry_prompts = [
                _chunk_prompt(chunks[i], style, terms[i], missing[i] or None) for i in to_retry
            ]
            retries = ask_many_or_errors(llm, ChunkTranslation, system, retry_prompts)
            for i, result in zip(to_retry, retries, strict=True):
                new_problems = _check(chunks[i], result)
                if new_problems:
                    if problems[i]:
                        problems[i] = new_problems  # still broken -> English fallback below
                    continue  # a valid first translation with missing terms is kept
                assert isinstance(result, ChunkTranslation)
                new_missing = missing_terms(terms[i], result)
                if problems[i] or len(new_missing) <= len(missing[i]):
                    results[i], problems[i], missing[i] = result, [], new_missing
        failed = [i for i in range(len(chunks)) if problems[i]]

        title_result = ask_many_or_errors(
            llm, TitleTranslation, system, [_title_prompt(title, style)]
        )[0]
        title_ok = isinstance(title_result, TitleTranslation) and bool(title_result.title.strip())

        if failed or not title_ok:
            reasons = [f"chunk {i} ({'; '.join(problems[i])})" for i in failed]
            if not title_ok:
                reasons.append("title")
            note = f"Urdu translation failed validation for {', '.join(reasons)}; showing English"
            return {"english": None, "trace": add_step(state, "urdu", note, started)}

        assert isinstance(title_result, TitleTranslation)
        urdu_chunks = [r.to_chunk() for r in results if isinstance(r, ChunkTranslation)]
        note = f"Translated {len(urdu_chunks)} chunks to Urdu (retried: {len(to_retry)})"
        still_missing = [f"chunk {i}: {', '.join(m)}" for i, m in enumerate(missing) if m]
        if still_missing:
            note += f"; English terms still missing ({'; '.join(still_missing)})"
        return {
            "title": title_result.title.strip(),
            "chunks": urdu_chunks,
            "english": EnglishVersion(title=title, chunks=list(chunks)),
            "trace": add_step(state, "urdu", note, started),
        }

    return urdu
