import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from app.core.profiles.profile_manager import ProfileManager
from app.ui import theme
from app.ui.compile_panel import CompilePanel
from app.ui.controller_panel import ControllerPanel
from app.ui.io_mapping_panel import IOMappingPanel
from app.ui.ladder.canvas import LadderCanvas
from app.ui.project import Project, ProgramEntry
from app.ui.variables_panel import VariablesPanel

APP_TITLE = "IEC2ESP"

# (tree label, page key) - static pages. "Program" is handled separately
# since it's a parent with dynamic Main/Sub Program children.
TREE_ITEMS = [
    ("Controller", "controller"),
    ("Variables", "variables"),
    ("IO Mapping", "io_mapping"),
    ("Compile", "compile"),
]


class _ProgramRowWidget(QWidget):
    """Container for the "Program" tree row's label + add button."""

    def __init__(self, on_add):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel("Program"))
        layout.addStretch()

        add_btn = QToolButton()
        add_btn.setText("+")
        add_btn.setToolTip("Add Sub Program")
        add_btn.setFixedSize(18, 18)
        add_btn.clicked.connect(on_add)
        layout.addWidget(add_btn)


class MainWindow(QMainWindow):
    def __init__(self, theme_mode: str = "light") -> None:
        super().__init__()
        self.setMinimumSize(1100, 750)
        self._theme_mode = theme_mode
        self._apply_titlebar_mode(theme_mode)

        profiles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "profiles"))
        self.profile_manager = ProfileManager(profiles_dir)

        self.project = Project()
        self.current_file_path: str | None = None
        self.is_modified = False
        self._closing_confirmed = False

        self._page_widgets: dict[str, object] = {}
        self._program_panels: dict[str, LadderCanvas] = {}
        self._build_menu_bar()
        self._build_central_widget()
        self._apply_project_to_panels()
        self._update_window_title()

    def _apply_titlebar_mode(self, mode: str) -> None:
        """Match the native Windows title bar to the resolved theme so it
        doesn't clash with the app body. No-op on other platforms/failure."""
        if sys.platform != "win32":
            return
        try:
            import ctypes

            hwnd = int(self.winId())
            value = ctypes.c_int(1 if mode == "dark" else 0)
            for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE across Windows 10/11 builds
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                )
                if result == 0:
                    break
        except Exception:
            pass

    # ---- UI construction ----

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save Project &As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        saved_mode = theme.load_saved_mode()
        self._theme_actions = {}
        for mode, label in (("light", "Light"), ("dark", "Dark"), ("system", "Follow System")):
            action = theme_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(mode == saved_mode)
            action.triggered.connect(lambda checked=False, m=mode: self._set_theme_mode(m))
            theme_group.addAction(action)
            self._theme_actions[mode] = action

        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_central_widget(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(220)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        self.tree.currentItemChanged.connect(self._on_tree_selection_changed)
        splitter.addWidget(self.tree)

        self.pages = QStackedWidget()
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(1, 1)

        self.variables_panel = VariablesPanel()
        self.controller_panel = ControllerPanel(self.profile_manager)
        self.io_mapping_panel = IOMappingPanel(self.profile_manager)
        self.compile_panel = CompilePanel()

        self._page_widgets = {
            "controller": self.controller_panel,
            "variables": self.variables_panel,
            "io_mapping": self.io_mapping_panel,
            "compile": self.compile_panel,
        }
        for widget in self._page_widgets.values():
            self.pages.addWidget(widget)

        for panel in (self.variables_panel, self.controller_panel, self.io_mapping_panel):
            panel.changed.connect(self._mark_modified)
        # Controller type affects the IO mapping panel's pin range; variable
        # renames affect its tag choices - just refresh it on any such change.
        self.controller_panel.changed.connect(self.io_mapping_panel.refresh)
        self.variables_panel.changed.connect(self.io_mapping_panel.refresh)

        self._populate_tree()

        self.setCentralWidget(splitter)
        self.statusBar().showMessage("Ready")

    def _populate_tree(self) -> None:
        first_item = None
        for label, page_key in TREE_ITEMS:
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, page_key)
            self.tree.addTopLevelItem(item)
            if first_item is None:
                first_item = item
            if page_key == "controller":
                self.controller_item = item
                # "Program" is a parent with dynamic Main/Sub Program
                # children (rebuilt by _rebuild_program_tree) - it has no
                # page of its own, so it carries no UserRole data.
                self.program_item = QTreeWidgetItem([""])
                self.tree.addTopLevelItem(self.program_item)
                self.tree.setItemWidget(self.program_item, 0, _ProgramRowWidget(self._add_sub_program))
                self.program_item.setExpanded(True)
        if first_item is not None:
            self.tree.setCurrentItem(first_item)

    # ---- Program tree (Main + Sub Programs) ----

    def _rebuild_program_tree(self) -> None:
        self.program_item.takeChildren()
        for program in self.project.programs:
            child = QTreeWidgetItem([program.name])
            child.setData(0, Qt.ItemDataRole.UserRole, ("program", program.uid))
            self.program_item.addChild(child)

    def _find_program(self, uid: str) -> ProgramEntry | None:
        for program in self.project.programs:
            if program.uid == uid:
                return program
        return None

    def _select_program_by_uid(self, uid: str) -> None:
        for i in range(self.program_item.childCount()):
            child = self.program_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, tuple) and data[1] == uid:
                self.tree.setCurrentItem(child)
                return

    def _get_or_create_program_panel(self, program: ProgramEntry) -> LadderCanvas:
        panel = self._program_panels.get(program.uid)
        if panel is None:
            panel = LadderCanvas(
                get_available_tags=lambda: [v.name for v in self.project.variables],
                get_program_names=lambda: [n for n in self.project.program_names() if n != program.name],
                on_changed=self._mark_modified,
            )
            panel.set_project_entry(program)
            self._program_panels[program.uid] = panel
            self.pages.addWidget(panel)
        return panel

    def _add_sub_program(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Sub Program", "Sub Program name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if name.lower() in {n.lower() for n in self.project.program_names()}:
            QMessageBox.warning(self, "Add Sub Program", f"A program named '{name}' already exists.")
            return
        new_program = ProgramEntry(name=name, kind="sub")
        self.project.programs.append(new_program)
        self._rebuild_program_tree()
        self._mark_modified()
        self._select_program_by_uid(new_program.uid)

    def _rename_program(self, program: ProgramEntry) -> None:
        new_name, ok = QInputDialog.getText(
            self, "Rename Program", "Name:", QLineEdit.EchoMode.Normal, program.name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == program.name:
            return
        others = {n.lower() for n in self.project.program_names() if n.lower() != program.name.lower()}
        if new_name.lower() in others:
            QMessageBox.warning(self, "Rename Program", f"A program named '{new_name}' already exists.")
            return
        QMessageBox.information(
            self,
            "Rename Program",
            f"Renamed to '{new_name}'.\n\nAny JSR({program.name}) calls elsewhere still reference the "
            "old name - Compile will flag those so you can update them.",
        )
        program.name = new_name
        self._rebuild_program_tree()
        self._mark_modified()
        self._select_program_by_uid(program.uid)

    def _delete_program(self, program: ProgramEntry) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Sub Program",
            f"Delete '{program.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.project.programs.remove(program)
        panel = self._program_panels.pop(program.uid, None)
        if panel is not None:
            self.pages.removeWidget(panel)
            panel.deleteLater()
        self._rebuild_program_tree()
        self._mark_modified()
        if self.program_item.childCount() > 0:
            self.tree.setCurrentItem(self.program_item.child(0))

    def _on_tree_context_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not (isinstance(data, tuple) and data[0] == "program"):
            return
        program = self._find_program(data[1])
        if program is None:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self._rename_program(program))
        if program.kind == "sub":
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_program(program))
        menu.exec(self.tree.mapToGlobal(position))

    # ---- page switching ----

    def _on_tree_selection_changed(self, current: QTreeWidgetItem, _previous: QTreeWidgetItem) -> None:
        if current is None:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        if isinstance(data, tuple) and data[0] == "program":
            program = self._find_program(data[1])
            if program is None:
                return
            self.pages.setCurrentWidget(self._get_or_create_program_panel(program))
            return
        widget = self._page_widgets.get(data)
        if widget is not None:
            self.pages.setCurrentWidget(widget)

    # ---- project lifecycle ----

    def _apply_project_to_panels(self) -> None:
        for widget in self._page_widgets.values():
            widget.set_project(self.project)
        for panel in self._program_panels.values():
            self.pages.removeWidget(panel)
            panel.deleteLater()
        self._program_panels.clear()
        self._rebuild_program_tree()
        self.tree.setCurrentItem(self.controller_item)

    def _mark_modified(self) -> None:
        self.is_modified = True
        self._update_window_title()

    def _update_window_title(self) -> None:
        name = self.project.name
        suffix = " *" if self.is_modified else ""
        self.setWindowTitle(f"{APP_TITLE} - {name}{suffix}")

    def _check_unsaved_changes(self) -> bool:
        """Returns True if it's safe to proceed (discarded, saved, or clean)."""
        if not self.is_modified:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. What would you like to do?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if reply == QMessageBox.StandardButton.Save:
            return self.save_project()
        return reply == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if not self._check_unsaved_changes():
            return
        self.project = Project()
        self.current_file_path = None
        self.is_modified = False
        self._apply_project_to_panels()
        self._update_window_title()
        self.statusBar().showMessage("New project created")

    def open_project(self) -> None:
        if not self._check_unsaved_changes():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "IEC2ESP Project (*.iec2esp.json);;All Files (*)")
        if not path:
            return
        try:
            self.project = Project.load(path)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Open Failed", f"Could not open project:\n{exc}")
            return
        self.current_file_path = path
        self.is_modified = False
        self._apply_project_to_panels()
        self._update_window_title()
        self.statusBar().showMessage(f"Opened {path}")

    def save_project(self) -> bool:
        if self.current_file_path:
            return self._save_to_path(self.current_file_path)
        return self.save_project_as()

    def save_project_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", f"{self.project.name}.iec2esp.json", "IEC2ESP Project (*.iec2esp.json);;All Files (*)"
        )
        if not path:
            return False
        return self._save_to_path(path)

    def _save_to_path(self, path: str) -> bool:
        try:
            self.project.save(path)
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save project:\n{exc}")
            return False
        self.current_file_path = path
        self.is_modified = False
        self._update_window_title()
        self.statusBar().showMessage(f"Saved {path}")
        return True

    def _set_theme_mode(self, mode: str) -> None:
        previous_mode = theme.load_saved_mode()
        if mode == previous_mode:
            return
        reply = QMessageBox.question(
            self,
            "Restart Required",
            f"Switch to the {mode.title()} theme?\n\nIEC2ESP needs to restart to apply this.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if reply != QMessageBox.StandardButton.Ok:
            self._theme_actions[previous_mode].setChecked(True)
            return
        if not self._check_unsaved_changes():
            self._theme_actions[previous_mode].setChecked(True)
            return
        theme.save_mode(mode)
        self._restart_application()

    def _restart_application(self) -> None:
        cmd = [sys.executable]
        if not getattr(sys, "frozen", False):
            cmd.append(os.path.abspath(sys.argv[0]))
        cmd.extend(sys.argv[1:])
        subprocess.Popen(cmd)
        self._closing_confirmed = True  # already handled unsaved changes above
        self.close()
        QApplication.instance().quit()

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "About IEC2ESP",
            "IEC2ESP\nConvert IEC 61131-3 (Structured Text, Ladder Logic) into C for ESP32.",
        )

    def closeEvent(self, event) -> None:
        if self._closing_confirmed or self._check_unsaved_changes():
            event.accept()
        else:
            event.ignore()
