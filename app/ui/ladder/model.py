"""In-memory ladder rung model + lossless-for-our-own-output conversion to
and from the backbone's flat text DSL (`condition -> output`, condition =
branch & branch | branch & branch). See app/core/ladder/ladder_to_st.py and
app/core/validation.py for the DSL this must stay in sync with."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Contact:
    tag: str = ""  # NO contact only - the DSL has no NOT/NC token


class Coil:
    """Base class for anything that can appear as a rung's output."""


@dataclass
class OutputCoil(Coil):
    tag: str = ""


@dataclass
class TimerCoil(Coil):
    name: str = "T1"
    preset_ms: int = 1000


@dataclass
class JsrCoil(Coil):
    name: str = ""  # target Sub Program name


@dataclass
class Branch:
    contacts: list[Contact] = field(default_factory=list)


@dataclass
class Rung:
    branches: list[Branch] = field(default_factory=lambda: [Branch()])
    coils: list[Coil] = field(default_factory=list)
    comment: str = ""
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


def _flatten_condition(branches: list[Branch]) -> str:
    return " | ".join(" & ".join(c.tag for c in b.contacts) for b in branches)


def _coil_text(coil: Coil) -> str:
    if isinstance(coil, JsrCoil):
        return f"JSR({coil.name})"
    if isinstance(coil, TimerCoil):
        return f"{coil.name}({coil.preset_ms})"
    if isinstance(coil, OutputCoil):
        return coil.tag
    raise TypeError(f"Unknown coil type: {type(coil).__name__}")


def _parse_branches(condition_text: str) -> list[Branch]:
    branches = [
        Branch(contacts=[Contact(tag=tag.strip()) for tag in branch_text.split("&") if tag.strip()])
        for branch_text in condition_text.split("|")
    ]
    return branches or [Branch()]


def _parse_coil(output_text: str) -> Coil:
    if output_text.startswith("JSR(") and output_text.endswith(")"):
        return JsrCoil(name=output_text[len("JSR("):-1].strip())
    if "(" in output_text and output_text.endswith(")"):
        name, preset_text = output_text.split("(", 1)
        preset_text = preset_text.rstrip(")").strip()
        try:
            preset_ms = int(preset_text)
        except ValueError:
            preset_ms = 1000
        return TimerCoil(name=name.strip(), preset_ms=preset_ms)
    return OutputCoil(tag=output_text)


def parse_program(text: str) -> list[Rung]:
    """DSL text -> rungs. One Rung per line first, then adjacent lines with
    identical condition text merge into one multi-coil Rung - matches what
    this module's own flatten_program always produces, so anything the
    canvas itself wrote round-trips exactly. Hand-written text with
    non-adjacent duplicate conditions just stays as separate rungs."""
    rungs: list[Rung] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "->" not in line:
            continue
        condition_text, output_text = (part.strip() for part in line.split("->", 1))
        coil = _parse_coil(output_text)
        if rungs and _flatten_condition(rungs[-1].branches) == condition_text:
            rungs[-1].coils.append(coil)
        else:
            rungs.append(Rung(branches=_parse_branches(condition_text), coils=[coil]))
    if not rungs:
        rungs.append(Rung())
    return rungs


def flatten_program(rungs: list[Rung]) -> str:
    """Rungs -> DSL text. Incomplete rungs (an empty branch, or no coils at
    all - both valid mid-edit states in the canvas) are silently omitted
    rather than emitted as broken DSL; the canvas keeps showing them for
    continued editing."""
    lines = []
    for rung in rungs:
        branches = [b for b in rung.branches if b.contacts]
        if not branches or not rung.coils:
            continue
        condition = _flatten_condition(branches)
        for coil in rung.coils:
            lines.append(f"{condition} -> {_coil_text(coil)}")
    return "\n".join(lines)
