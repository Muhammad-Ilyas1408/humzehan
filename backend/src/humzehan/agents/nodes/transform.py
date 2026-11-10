"""Transform nodes: rewrite the source into the chosen learning style.

One factory builds the three nodes (focus / easyread / literal); only the prompt differs.
On a re-run (after the checker), only non-approved chunks are rewritten, using the
checker's reasons. Rewritten chunks get an empty quiz so the quiz node regenerates it.
"""

from langchain_core.language_models import BaseChatModel

from humzehan.agents.nodes._common import Node, add_step, ask, ask_many, start_timer
from humzehan.agents.nodes.router import TRANSFORM_NODES
from humzehan.agents.prompts import load_prompt
from humzehan.agents.state import AgentState, ChunkDraft, ChunkReview, TransformOutput
from humzehan.schemas.lesson import Chunk, LearningMode


def _first_pass_prompt(source_text: str) -> str:
    return f"SOURCE:\n{source_text}\n\nRewrite the SOURCE as a lesson."


def _rewrite_prompt(source_text: str, chunk: Chunk, review: ChunkReview) -> str:
    previous = chunk.model_dump_json(include={"heading", "body", "hook", "glossary"}, indent=2)
    return (
        f"SOURCE:\n{source_text}\n\n"
        f"PREVIOUS CHUNK (chunk {review.chunk_index}):\n{previous}\n\n"
        f"CHECKER: {review.action} - {review.reason}\n"
        f"QUOTE: {review.quote or '(none)'}\n\n"
        "Rewrite only this chunk. Fix only the quoted problem; "
        "do not add any sentence that is not supported by the SOURCE."
    )


def make_transform_node(llm: BaseChatModel, mode: LearningMode) -> Node:
    node_name = TRANSFORM_NODES[mode]
    system = load_prompt(mode.value)

    def transform(state: AgentState) -> AgentState:
        started = start_timer()
        source_text = state["source_text"]
        pending = [r for r in state.get("reviews", []) if r.action != "approve"]
        chunks = state.get("chunks", [])

        if not chunks or not pending:
            output = ask(llm, TransformOutput, system, _first_pass_prompt(source_text))
            new_chunks = [draft.to_chunk() for draft in output.chunks]
            note = f"Wrote {len(new_chunks)} chunks in {mode.value} style"
            return {
                "title": output.title,
                "chunks": new_chunks,
                "reviews": [],
                "trace": add_step(state, node_name, note, started),
            }

        new_chunks = list(chunks)
        users = [_rewrite_prompt(source_text, chunks[r.chunk_index], r) for r in pending]
        drafts = ask_many(llm, ChunkDraft, system, users)  # parallel, same order as pending
        for review, draft in zip(pending, drafts, strict=True):
            new_chunks[review.chunk_index] = draft.to_chunk()
        loops = state.get("loops", 0) + 1
        rewritten = ", ".join(str(r.chunk_index) for r in pending)
        note = f"Rewrite round {loops}: chunks {rewritten}"
        return {
            "chunks": new_chunks,
            "loops": loops,
            "trace": add_step(state, node_name, note, started),
        }

    transform.__name__ = node_name
    return transform
