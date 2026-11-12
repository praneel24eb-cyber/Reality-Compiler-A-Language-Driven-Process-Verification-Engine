"""Persistable guided workflow input: user answers are the source of truth."""

from pydantic import Field

from app.models import Contract

QUESTIONS = [
    "Who takes part, and what is each person's or team's responsibility?",
    "What starts the process? Describe the normal steps in order and the successful outcome.",
    "Where are decisions made? Give the conditions and the next step for each outcome.",
    "What happens on rejection, an exception, or failure? Say 'not defined' for unknown paths.",
    "Which steps must never be skipped, and before which outcomes? Say 'none' if there are no such requirements.",
]


class NewDraft(Contract):
    goal: str = Field(min_length=1, max_length=3000, pattern=r"\S")


class DraftAnswer(Contract):
    turn: int = Field(ge=0, lt=len(QUESTIONS))
    answer: str = Field(min_length=1, max_length=4000, pattern=r"\S")


def draft_view(identifier: str, data: dict) -> dict:
    answers = data["answers"]
    messages = [{"role": "user", "content": data["goal"]}]
    for question, answer in zip(QUESTIONS, answers):
        messages += [{"role": "assistant", "content": question}, {"role": "user", "content": answer}]
    if len(answers) < len(QUESTIONS):
        messages.append({"role": "assistant", "content": QUESTIONS[len(answers)]})
    else:
        messages.append({"role": "assistant", "content": "Your answers are saved. Generate the workflow to see its steps, branches, and review findings here."})
    return {"id": identifier, **data, "messages": messages, "ready": len(answers) == len(QUESTIONS)}


def draft_source(data: dict) -> str:
    if len(data["answers"]) != len(QUESTIONS):
        raise ValueError("Answer the remaining questions before generating the workflow")
    return "Goal: " + data["goal"] + "\n\n" + "\n\n".join(
        question + "\nUser answer: " + answer
        for question, answer in zip(QUESTIONS, data["answers"])
    )
