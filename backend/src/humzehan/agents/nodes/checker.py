"""Checker node: review every chunk against the source and the style rules.

The whole lesson goes to the LLM in one call, so missing facts are judged across all chunks.
Every flag carries evidence; flags whose evidence does not hold up are dropped in code
(see ``agents/verification.py``) and counted in the trace note.

Before the call, a deterministic grounding pre-check finds "suspect" sentences (few of their
words are in the SOURCE). The checker must judge each one; confirmed ones become fix_fact.
"""

from langchain_core.language_models import BaseChatModel

from humzehan.agents.nodes._common import Node, add_step, ask, start_timer
from humzehan.agents.prompts import load_prompt, style_rules
from humzehan.agents.state import AgentState, CheckerOutput, ChunkReview
from humzehan.agents.verification import (
    SuspectSentence,
    apply_suspect_judgments,
    find_suspect_sentences,
    verify_reviews,
)
from humzehan.schemas.lesson import Chunk, LearningMode


def _lesson_text(chunks: list[Chunk]) -> str:
    parts = []
    for index, chunk in enumerate(chunks):
        glossary = "; ".join(f"{g.term}: {g.meaning}" for g in chunk.glossary) or "none"
        parts.append(
            f"--- chunk {index} ---\nHeading: {chunk.heading}\nHook: {chunk.hook or 'none'}\n"
            f"Body:\n{chunk.body}\nGlossary: {glossary}"
        )
    return "\n\n".join(parts)


def _suspects_text(suspects: list[SuspectSentence]) -> str:
    if not suspects:
        return "none"
    return "\n".join(
        f'[{i}] chunk {s.chunk_index}: "{s.sentence}" ({s.share:.0%} of its words in SOURCE)'
        for i, s in enumerate(suspects)
    )


def _describe(review: ChunkReview) -> str:
    text = f"Chunk {review.chunk_index}: {review.action} ({review.reason})"
    return f'{text} quote="{review.quote}"' if review.quote else text


def make_checker_node(llm: BaseChatModel) -> Node:
    template = load_prompt("checker")

    def checker(state: AgentState) -> AgentState:
        started = start_timer()
        chunks = state.get("chunks", [])
        mode = LearningMode(state["mode"])
        suspects = find_suspect_sentences(chunks, state["source_text"])
        system = template.replace("{style_rules}", style_rules(mode.value))
        user = (
            f"LEARNING STYLE: {mode.value}\n\n"
            f"SOURCE:\n{state['source_text']}\n\n"
            f"LESSON (all {len(chunks)} chunks; judge missing facts across the whole lesson):\n"
            f"{_lesson_text(chunks)}\n\n"
            "SUSPECT SENTENCES (judge every one in suspect_judgments):\n"
            f"{_suspects_text(suspects)}"
        )
        output = ask(llm, CheckerOutput, system, user)
        verified = verify_reviews(output.reviews, chunks, state["source_text"])
        outcome = apply_suspect_judgments(verified.reviews, suspects, output.suspect_judgments)
        flagged = [r for r in outcome.reviews if r.action != "approve"]
        parts = [_describe(r) for r in flagged] or [f"All {len(chunks)} chunks approved"]
        if suspects:
            judged = (
                f"suspects: {len(suspects)} ({len(outcome.unsupported)} unsupported, "
                f"{len(outcome.supported)} supported"
            )
            if outcome.unjudged:
                judged += f", {len(outcome.unjudged)} not judged"
            parts.append(judged + ")")
        else:
            parts.append("suspects: 0")
        if verified.dropped:
            count = len(verified.dropped)
            details = "; ".join(
                f"chunk {d.review.chunk_index} {d.review.action}: {d.why}" for d in verified.dropped
            )
            parts.append(f"dropped {count} unverified flag{'s' if count != 1 else ''} ({details})")
        note = "; ".join(parts)
        return {"reviews": outcome.reviews, "trace": add_step(state, "checker", note, started)}

    return checker
