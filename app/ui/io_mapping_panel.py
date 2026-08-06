"""Pin assignment table. Each row's tag is chosen from declared variables;
the pin range is clamped to the selected controller profile's pin_count
when the profile is pin-based (e.g. ESP32), matching app/profiles/*.json."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QSpinBox,
    QStyle,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.project import IOMappingEntry, Project

PHYSICAL_IO_TYPES = [
    "Digital Input", "Digital Output", "Analog Input", "Analog Output",
    "PWM Output", "UART TX", "UART RX",
]


class IOMappingPanel(QWidget):
    changed = Signal()

    def __init__(self, profile_manager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.project: Project | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 5)
        self.table.setToolTip("Assign a GPIO pin to each physical I/O tag.")
        self.table.setHorizontalHeaderLabels(["Tag", "Pin", "Type", "Pull-up", ""])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 32)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        add_row = QHBoxLayout()
        add_btn = QPushButton("Add Mapping")
        add_btn.clicked.connect(self.add_mapping)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.refresh()

    def _current_profile(self) -> dict | None:
        if self.project is None:
            return None
        return self.profile_manager.get_profile(self.project.controller_type)

    def _pin_count(self) -> int | None:
        profile = self._current_profile()
        if profile and "pin_count" in profile:
            return profile["pin_count"]
        return None

    def _tag_choices(self) -> list[str]:
        if self.project is None:
            return []
        return [v.name for v in self.project.variables]

    def refresh(self) -> None:
        if self.project is None:
            return
        self.table.setRowCount(0)
        for index, entry in enumerate(self.project.io_mapping):
            self._insert_row(index, entry)

    def _insert_row(self, index: int, entry: IOMappingEntry) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        tag_combo = QComboBox()
        tag_combo.setEditable(True)
        tag_combo.addItems(self._tag_choices())
        tag_combo.setCurrentText(entry.tag)
        tag_combo.currentTextChanged.connect(
            lambda text, idx=index: self._on_field_changed(idx, "tag", text)
        )
        self.table.setCellWidget(row, 0, tag_combo)

        pin_spin = QSpinBox()
        pin_count = self._pin_count()
        pin_spin.setRange(0, (pin_count - 1) if pin_count else 255)
        pin_spin.setValue(entry.pin)
        pin_spin.valueChanged.connect(
            lambda value, idx=index: self._on_field_changed(idx, "pin", value)
        )
        self.table.setCellWidget(row, 1, pin_spin)

        type_combo = QComboBox()
        type_combo.addItems(PHYSICAL_IO_TYPES)
        type_combo.setCurrentText(entry.var_type)
        type_combo.currentTextChanged.connect(
            lambda text, idx=index: self._on_field_changed(idx, "var_type", text)
        )
        self.table.setCellWidget(row, 2, type_combo)

        pullup_check = QCheckBox()
        pullup_check.setChecked(entry.pullup)
        pullup_check.toggled.connect(
            lambda checked, idx=index: self._on_field_changed(idx, "pullup", checked)
        )
        self.table.setCellWidget(row, 3, pullup_check)

        remove_btn = QToolButton()
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        remove_btn.setToolTip("Delete mapping")
        remove_btn.clicked.connect(lambda _checked=False, idx=index: self.delete_mapping(idx))
        self.table.setCellWidget(row, 4, remove_btn)

    def _on_field_changed(self, index: int, field_name: str, value) -> None:
        if self.project is None or index >= len(self.project.io_mapping):
            return
        setattr(self.project.io_mapping[index], field_name, value)
        self.changed.emit()

    def add_mapping(self) -> None:
        if self.project is None:
            return
        self.project.io_mapping.append(IOMappingEntry(tag="", pin=0, var_type="Digital Input"))
        self.refresh()
        self.changed.emit()

    def delete_mapping(self, index: int) -> None:
        if self.project is None or index >= len(self.project.io_mapping):
            return
        del self.project.io_mapping[index]
        self.refresh()
        self.changed.emit()
