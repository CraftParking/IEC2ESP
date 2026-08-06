"""Compile action: runs app.core.validation.validation() once per program,
then two UI-side checks with no backbone involvement (every JSR(...) target
must be a declared program, and the call graph must be acyclic - generated
C has no stack-depth protection, so a JSR cycle means infinite recursion at
runtime), and only calls app.core.compiler.compile_programs_to_c() if none
of that produced an [ERROR] ([WARNING] issues don't block compilation)."""

import re
from pathlib import Path

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from app.core.compiler import compile_programs_to_c
from app.core.validation import validation
from app.ui import theme
from app.ui.project import Project

JSR_PATTERN = re.compile(r"JSR\((\w+)\)")


class CompilePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self._last_generated_code: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        button_row = QHBoxLayout()
        compile_btn = QPushButton("Compile")
        compile_btn.setObjectName("primary")
        compile_btn.clicked.connect(self.compile)
        self.save_btn = QPushButton("Save Generated Code (.ino)")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_output)
        button_row.addWidget(compile_btn)
        button_row.addWidget(self.save_btn)
        button_row.addStretch()
        layout.addLayout(button_row)

        splitter = QSplitter(Qt.Orientation.Vertical)

        issues_container = QWidget()
        issues_layout = QVBoxLayout(issues_container)
        issues_layout.setContentsMargins(0, 0, 0, 0)
        issues_layout.addWidget(QLabel("Validation"))
        self.issues_list = QListWidget()
        issues_layout.addWidget(self.issues_list)
        splitter.addWidget(issues_container)

        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(QLabel("Generated C"))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        output_layout.addWidget(self.output)
        splitter.addWidget(output_container)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.issues_list.clear()
        self.output.clear()
        self._last_generated_code = None
        self.save_btn.setEnabled(False)

    def compile(self) -> None:
        if self.project is None:
            return

        program_texts = self.project.build_compiler_programs()
        mapping_rows = self.project.build_validation_mapping_rows()
        global_variables = self.project.build_validation_global_variables()

        issues: list[str] = []
        for program in self.project.programs:
            for message in validation(mapping_rows, program.ladder_text, global_variables):
                issues.append(f"[{program.name}] {message}")
        issues.extend(self._validate_jsr_calls(program_texts))

        all_empty = all(not text.strip() for text in program_texts.values())
        if all_empty and not issues:
            issues = ["[ERROR] No ladder program to compile"]

        has_errors = any("[ERROR]" in message for message in issues)
        if has_errors or all_empty:
            self._show_issues(issues)
            self.output.clear()
            self._last_generated_code = None
            self.save_btn.setEnabled(False)
            return

        # An empty IO Mapping table means "not configured yet" - let the
        # compiler auto-assign pins (its behavior for io_mapping=None) rather
        # than passing an empty dict, which instead means "every tag must be
        # explicitly mapped" and fails on the first one that isn't.
        io_mapping = self.project.build_compiler_io_mapping() or None
        controller_config = self.project.build_compiler_controller_config()
        main_name = self.project.main_program().name

        try:
            code = compile_programs_to_c(program_texts, main_name, io_mapping, controller_config)
        except KeyError as exc:
            missing = exc.args[0] if exc.args else "?"
            self._show_issues(issues + [f"[ERROR] '{missing}' has no IO mapping - add it in IO Mapping"])
            self.output.clear()
            self._last_generated_code = None
            self.save_btn.setEnabled(False)
            return
        except Exception as exc:  # noqa: BLE001 - surface any other compiler failure as a validation issue
            self._show_issues(issues + [f"[ERROR] Compilation failed: {exc}"])
            self.output.clear()
            self._last_generated_code = None
            self.save_btn.setEnabled(False)
            return

        self._show_issues(issues)
        self.output.setPlainText(code)
        self._last_generated_code = code
        self.save_btn.setEnabled(True)

    def _validate_jsr_calls(self, program_texts: dict[str, str]) -> list[str]:
        known_names = set(program_texts.keys())
        call_graph: dict[str, set[str]] = {}
        issues: list[str] = []

        for program_name, text in program_texts.items():
            targets = set(JSR_PATTERN.findall(text))
            call_graph[program_name] = targets
            for target in targets:
                if target not in known_names:
                    issues.append(f"[{program_name}] [ERROR] JSR target '{target}' is not a declared Sub Program")

        cycle = self._find_jsr_cycle(call_graph)
        if cycle:
            issues.append(f"[ERROR] Recursive JSR call: {' -> '.join(cycle)}")

        return issues

    @staticmethod
    def _find_jsr_cycle(call_graph: dict[str, set[str]]) -> list[str] | None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str, path: list[str]) -> list[str] | None:
            if node in visiting:
                return path[path.index(node):] + [node]
            if node in visited:
                return None
            visiting.add(node)
            for neighbor in call_graph.get(node, ()):
                if neighbor in call_graph:  # dangling targets are already flagged separately
                    result = dfs(neighbor, path + [node])
                    if result:
                        return result
            visiting.discard(node)
            visited.add(node)
            return None

        for start in call_graph:
            result = dfs(start, [])
            if result:
                return result
        return None

    def _show_issues(self, issues: list[str]) -> None:
        self.issues_list.clear()
        if not issues:
            self.issues_list.addItem(QListWidgetItem("No issues found."))
            return
        for message in issues:
            item = QListWidgetItem(message)
            if "[ERROR]" in message:
                item.setForeground(QColor(theme.ERROR))
            elif "[WARNING]" in message:
                item.setForeground(QColor(theme.WARNING))
            self.issues_list.addItem(item)

    def save_output(self) -> None:
        if not self._last_generated_code:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Generated Code", "", "Arduino Sketch (*.ino);;All Files (*)"
        )
        if path:
            Path(path).write_text(self._last_generated_code, encoding="utf-8")
