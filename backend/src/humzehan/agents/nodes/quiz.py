"""Quiz node: add 3 questions to every chunk that does not have a quiz yet (in parallel)."""

from langchain_core.language_models import BaseChatModel

from humzehan.agents.nodes._common import Node, add_step, ask_many, start_timer
from humzehan.agents.prompts import load_prompt
from humzehan.agents.state import AgentState, QuizSet


def make_quiz_node(llm: BaseChatModel) -> Node:
    system = load_prompt("quiz")

    def quiz(state: AgentState) -> AgentState:
        started = start_timer()
        chunks = list(state.get("chunks", []))
        done = [index for index, chunk in enumerate(chunks) if not chunk.quiz]
        users = [
            f"CHUNK:\n## {chunks[i].heading}\n\n{chunks[i].body}\n\nWrite the quiz." for i in done
        ]
        for index, quiz_set in zip(done, ask_many(llm, QuizSet, system, users), strict=True):
            chunks[index] = chunks[index].model_copy(update={"quiz": quiz_set.questions})
        note = (
            f"3 questions for chunks {', '.join(map(str, done))}"
            if done
            else "All chunks already have a quiz"
        )
        return {"chunks": chunks, "trace": add_step(state, "quiz", note, started)}

    return quiz
