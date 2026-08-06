"""Tag/variable table - one flat list, matching exactly what
app.core.validation.validation() expects for its global_variables argument.
`description` is an additive field the backbone never sees."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.project import Project, Variable

ALL_TYPES = [
    "Digital Input", "Digital Output", "Analog Input", "Analog Output",
    "PWM Output", "UART TX", "UART RX", "TON", "BOOL", "INT", "REAL", "STRING",
]


class VariablesPanel(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Project | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Address", "Description", ""])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 32)
        self.table.verticalHeader().setVisible(False)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table)

        add_row = QHBoxLayout()
        add_btn = QPushButton("Add Variable")
        add_btn.clicked.connect(self.add_variable)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.refresh()

    def refresh(self) -> None:
        if self.project is None:
            return
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for index in range(len(self.project.variables)):
            self._insert_row(index)
        self.table.blockSignals(False)

    def _insert_row(self, index: int) -> None:
        variable = self.project.variables[index]
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(variable.name)
        name_item.setData(Qt.ItemDataRole.UserRole, index)
        self.table.setItem(row, 0, name_item)

        combo = QComboBox()
        combo.addItems(ALL_TYPES)
        if variable.type not in ALL_TYPES:
            combo.addItem(variable.type)
        combo.setCurrentText(variable.type)
        combo.currentTextChanged.connect(lambda text, idx=index: self._on_type_changed(idx, text))
        self.table.setCellWidget(row, 1, combo)

        self.table.setItem(row, 2, QTableWidgetItem(variable.address))
        self.table.setItem(row, 3, QTableWidgetItem(variable.description))

        remove_btn = QToolButton()
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        remove_btn.setToolTip("Delete variable")
        remove_btn.clicked.connect(lambda _checked=False, idx=index: self.delete_variable(idx))
        self.table.setCellWidget(row, 4, remove_btn)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self.project is None:
            return
        row = item.row()
        name_item = self.table.item(row, 0)
        if name_item is None:
            return
        index = name_item.data(Qt.ItemDataRole.UserRole)
        if index is None or index >= len(self.project.variables):
            return
        variable = self.project.variables[index]
        variable.name = self.table.item(row, 0).text().strip()
        variable.address = self.table.item(row, 2).text().strip()
        variable.description = self.table.item(row, 3).text().strip()
        self.changed.emit()

    def _on_type_changed(self, index: int, text: str) -> None:
        if self.project is None or index >= len(self.project.variables):
            return
        self.project.variables[index].type = text
        self.changed.emit()

    def add_variable(self) -> None:
        if self.project is None:
            return
        existing = {v.name for v in self.project.variables}
        n = 1
        while f"VAR{n}" in existing:
            n += 1
        self.project.variables.append(Variable(name=f"VAR{n}", type="BOOL"))
        self.refresh()
        self.changed.emit()

    def delete_variable(self, index: int) -> None:
        if self.project is None or index >= len(self.project.variables):
            return
        del self.project.variables[index]
        self.refresh()
        self.changed.emit()
