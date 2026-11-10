"""Agent state and the structured-output models the LLM must return."""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from humzehan.schemas.lesson import Chunk, GlossaryItem, LearningMode, QuizItem, TraceStep

CheckerAction = Literal["approve", "simplify", "add_glossary", "fix_fact", "missing_fact"]


class ChunkReview(BaseModel):
    chunk_index: int
    action: CheckerAction
    reason: str
    quote: str | None = Field(
        description=(
            "Evidence. fix_fact: the exact sentence from the chunk that the SOURCE does not "
            "support. missing_fact: the exact SOURCE sentence that no chunk covers. "
            "Otherwise null."
        )
    )


class AgentState(TypedDict, total=False):
    source_text: str
    image_b64: str | None  # F4
    mode: LearningMode
    urdu: bool  # F5
    title: str
    chunks: list[Chunk]
    reviews: list[ChunkReview]
    loops: int  # number of rewrite rounds done
    trace: list[TraceStep]


# --- Structured outputs requested from the LLM (all fields required) ---


class ChunkDraft(BaseModel):
    """One rewritten chunk, before quiz questions are added."""

    heading: str
    body: str = Field(description="Markdown body of the chunk")
    hook: str | None = Field(description='One-line "why this matters" (Focus only), else null')
    glossary: list[GlossaryItem]

    def to_chunk(self) -> Chunk:
        return Chunk(heading=self.heading, body=self.body, hook=self.hook, glossary=self.glossary)


class TransformOutput(BaseModel):
    title: str
    chunks: list[ChunkDraft] = Field(min_length=1)


class QuizSet(BaseModel):
    questions: list[QuizItem] = Field(min_length=3, max_length=3)


class SuspectJudgment(BaseModel):
    """The checker's verdict on one suspect sentence from the grounding pre-check."""

    suspect_id: int
    supported: bool = Field(description="True only if the SOURCE states this (paraphrase is ok)")
    reason: str


class CheckerOutput(BaseModel):
    reviews: list[ChunkReview]
    suspect_judgments: list[SuspectJudgment] = Field(
        description="One judgment per SUSPECT SENTENCE id; empty list if there are none"
    )
