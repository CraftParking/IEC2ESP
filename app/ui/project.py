"""Project data model: what gets saved/loaded, and the seam that translates
the UI's single IO-mapping table into the two different shapes the backbone
expects (validation() vs compile_st_to_c()/compile_ladder_to_c())."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.controller_config import ControllerConfig

DEFAULT_CONTROLLER_TYPE = "ESP32"


@dataclass
class Variable:
    name: str
    type: str = "BOOL"
    address: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "address": self.address,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Variable":
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "BOOL"),
            address=data.get("address", ""),
            description=data.get("description", ""),
        )


@dataclass
class IOMappingEntry:
    tag: str
    pin: int
    var_type: str = "Digital Input"
    pullup: bool = False

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "pin": self.pin,
            "var_type": self.var_type,
            "pullup": self.pullup,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IOMappingEntry":
        return cls(
            tag=data.get("tag", ""),
            pin=data.get("pin", 0),
            var_type=data.get("var_type", "Digital Input"),
            pullup=data.get("pullup", False),
        )


@dataclass
class ProgramEntry:
    """One program: the Main Program (always exactly one) or a Sub Program,
    only reachable via JSR(name) from Main or another Sub. `uid` is a stable
    key independent of `name`/list position, used to key per-program UI
    state (e.g. which LadderCanvas instance edits it) so renaming or
    reordering doesn't lose track of the right widget."""

    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Main Program"
    kind: str = "main"  # "main" | "sub"
    # Temporary raw-text ladder source per program. Replaced by a structured
    # rung model (app/ui/ladder/model.py) once the graphical canvas lands.
    ladder_text: str = ""

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "name": self.name,
            "kind": self.kind,
            "ladder_text": self.ladder_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProgramEntry":
        return cls(
            uid=data.get("uid") or uuid.uuid4().hex[:8],
            name=data.get("name", "Main Program"),
            kind=data.get("kind", "main"),
            ladder_text=data.get("ladder_text", ""),
        )


@dataclass
class Project:
    name: str = "Untitled Project"
    controller_type: str = DEFAULT_CONTROLLER_TYPE
    controller_config: ControllerConfig = field(default_factory=ControllerConfig)
    variables: list[Variable] = field(default_factory=list)
    io_mapping: list[IOMappingEntry] = field(default_factory=list)
    programs: list[ProgramEntry] = field(default_factory=lambda: [ProgramEntry()])
    file_path: str | None = None

    def main_program(self) -> ProgramEntry:
        for program in self.programs:
            if program.kind == "main":
                return program
        raise ValueError("Project has no Main Program")

    def sub_programs(self) -> list[ProgramEntry]:
        return [program for program in self.programs if program.kind == "sub"]

    def program_names(self) -> list[str]:
        return [program.name for program in self.programs]

    # ---- backbone integration shapes ----
    # validation() and compile_*_to_c() want different shapes for what is,
    # conceptually, the same IO mapping table. Build both from one place so
    # every caller stays consistent.

    def build_validation_mapping_rows(self) -> list[dict]:
        """Shape app.core.validation.validation()'s `mapping` argument wants."""
        return [
            {"pin": entry.pin, "tag": entry.tag, "type": entry.var_type}
            for entry in self.io_mapping
        ]

    def build_validation_global_variables(self) -> list[dict]:
        """Shape validation()'s `global_variables` argument wants."""
        return [variable.to_dict() for variable in self.variables]

    def build_compiler_io_mapping(self) -> dict:
        """Shape compile_st_to_c()/compile_ladder_to_c()'s `io_mapping` wants."""
        mapping = {}
        for entry in self.io_mapping:
            is_input = "input" in entry.var_type.lower()
            config = {"pin": entry.pin, "type": "input" if is_input else "output"}
            if is_input:
                config["pullup"] = entry.pullup
            mapping[entry.tag] = config
        return mapping

    def build_compiler_controller_config(self) -> dict:
        return self.controller_config.to_dict()

    def build_compiler_programs(self) -> dict[str, str]:
        """Shape app.core.compiler.compile_programs_to_c()'s `programs` argument wants."""
        return {program.name: program.ladder_text for program in self.programs}

    # ---- serialization ----

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "controller_type": self.controller_type,
            "controller_config": self.controller_config.to_dict(),
            "variables": [v.to_dict() for v in self.variables],
            "io_mapping": [m.to_dict() for m in self.io_mapping],
            "programs": [p.to_dict() for p in self.programs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        if "programs" in data:
            programs = [ProgramEntry.from_dict(p) for p in data["programs"]]
        else:
            # Back-compat: projects saved before Main/Sub Programs existed
            # had one flat `ladder_text` field - migrate it into a Main Program.
            programs = [ProgramEntry(name="Main Program", kind="main", ladder_text=data.get("ladder_text", ""))]
        return cls(
            name=data.get("name", "Untitled Project"),
            controller_type=data.get("controller_type", DEFAULT_CONTROLLER_TYPE),
            controller_config=ControllerConfig.from_dict(data.get("controller_config", {})),
            variables=[Variable.from_dict(v) for v in data.get("variables", [])],
            io_mapping=[IOMappingEntry.from_dict(m) for m in data.get("io_mapping", [])],
            programs=programs,
        )

    def save(self, path: str) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        self.file_path = path

    @classmethod
    def load(cls, path: str) -> "Project":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        project = cls.from_dict(data)
        project.file_path = path
        return project
