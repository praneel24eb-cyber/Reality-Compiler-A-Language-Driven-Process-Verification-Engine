"""The fixed public workflow contract; structural errors fail validation."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Sentence(Contract):
    id: str
    text: str
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class State(Contract):
    id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
    name: str = Field(min_length=1)
    kind: Literal["start", "normal", "terminal"]
    actor: str | None
    evidence: list[str] = Field(min_length=1)
    inferred: bool = False
    inference_reason: str | None

    @model_validator(mode="after")
    def inference(self) -> Self:
        if any(not item.strip() for item in self.evidence):
            raise ValueError("Evidence IDs must not be blank")
        if self.inferred and (not self.inference_reason or len(self.inference_reason.strip()) < 10):
            raise ValueError("Inferred elements need a meaningful inference reason")
        return self


class Transition(Contract):
    id: str = Field(min_length=1)
    source: str
    target: str
    label: str
    condition: str | None
    actor: str | None
    evidence: list[str] = Field(min_length=1)
    inferred: bool
    inference_reason: str | None

    @model_validator(mode="after")
    def inference(self) -> Self:
        if any(not item.strip() for item in self.evidence):
            raise ValueError("Evidence IDs must not be blank")
        if self.inferred and (not self.inference_reason or len(self.inference_reason.strip()) < 10):
            raise ValueError("Inferred elements need a meaningful inference reason")
        return self


class ProcessModel(Contract):
    process_id: str
    actors: list[str]
    states: list[State]
    transitions: list[Transition]

    @model_validator(mode="after")
    def references(self) -> Self:
        ids = {state.id for state in self.states}
        if len(ids) != len(self.states):
            raise ValueError("Duplicate state IDs")
        if len({edge.id for edge in self.transitions}) != len(self.transitions):
            raise ValueError("Duplicate transition IDs")
        if any(edge.source not in ids or edge.target not in ids for edge in self.transitions):
            raise ValueError("Transition references an unknown state")
        return self


class Finding(Contract):
    id: str
    type: Literal[
        "unsupported_element",
        "assumption",
        "missing_branch",
        "unstated_actor",
        "dead_end",
        "unreachable_state",
        "bypass",
        "invariant_violation",
    ]
    severity: Literal["info", "warning", "error"]
    location: str | None
    message: str
    evidence: list[str]
    counterexample_path: list[str] | None
    method: Literal["structural", "llm_review"] = "structural"
