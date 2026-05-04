from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.compiler import compile_st_to_c
from app.core.ladder.ladder_to_st import ladder_to_st
from app.core.validation import validation


class IOMappingWidget(QWidget):
    PIN_TYPES = ["Input", "Output", "Power", "Ground", "TX", "RX", "PWM", "Analog"]

    def __init__(self) -> None:
        super().__init__()
        self.rows = []

        self.pin_count = QSpinBox()
        self.pin_count.setRange(1, 100)
        self.pin_count.setValue(30)
        self.pin_count.valueChanged.connect(self.regenerate_grid)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Number of Pins"))
        controls.addWidget(self.pin_count)
        controls.addStretch()

        header = QGridLayout()
        header.addWidget(QLabel("Pin"), 0, 0)
        header.addWidget(QLabel("Tag Name"), 0, 1)
        header.addWidget(QLabel("Type"), 0, 2)

        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid_container = QWidget()
        grid_container_layout = QVBoxLayout()
        grid_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid_container_layout.addLayout(self.grid)
        grid_container_layout.addStretch()
        self.grid_container.setLayout(grid_container_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.grid_container)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addLayout(controls)
        layout.addLayout(header)
        layout.addWidget(scroll_area)
        self.setLayout(layout)

        self.regenerate_grid(self.pin_count.value())

    def regenerate_grid(self, pin_count: int) -> None:
        self.clear_grid()
        self.rows = []

        for row in range(pin_count):
            pin_number = row
            pin_label = QLabel(f"GPIO {pin_number}")
            tag_input = QLineEdit()
            pin_type = QComboBox()
            pin_type.addItems(self.PIN_TYPES)
            pin_type.currentTextChanged.connect(
                lambda selected_type, field=tag_input: self.update_tag_field(field, selected_type)
            )

            self.grid.addWidget(pin_label, row, 0, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(tag_input, row, 1, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(pin_type, row, 2, alignment=Qt.AlignmentFlag.AlignTop)
            self.rows.append(
                {
                    "pin": pin_number,
                    "tag_input": tag_input,
                    "type_combo": pin_type,
                }
            )

    def clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def update_tag_field(self, tag_input: QLineEdit, pin_type: str) -> None:
        is_logic_pin = pin_type in ("Input", "Output")
        tag_input.setEnabled(is_logic_pin)
        if not is_logic_pin:
            tag_input.clear()

    def get_mapping(self) -> dict:
        mapping = {}

        for row in self.rows:
            pin_type = row["type_combo"].currentText()
            tag_name = row["tag_input"].text().strip()

            if pin_type in ("Input", "Output") and tag_name:
                mapping[tag_name] = {
                    "pin": row["pin"],
                    "type": pin_type.lower(),
                }

        return mapping

    def get_validation_mapping(self) -> list[dict]:
        return [
            {
                "pin": row["pin"],
                "tag": row["tag_input"].text(),
                "type": row["type_combo"].currentText(),
            }
            for row in self.rows
        ]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IEC2ESP Ladder Compiler")
        self.setMinimumSize(900, 700)

        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderHidden(True)
        self.navigation_tree.currentItemChanged.connect(self.change_page)
        self.setup_navigation_tree()

        self.pages = QStackedWidget()
        self.io_mapping_page = self.create_io_mapping_page()
        self.ladder_editor_page = self.create_ladder_editor_page()
        self.pages.addWidget(self.io_mapping_page)
        self.pages.addWidget(self.ladder_editor_page)

        splitter = QSplitter()
        splitter.addWidget(self.navigation_tree)
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        self.setCentralWidget(splitter)
        self.navigation_tree.setCurrentItem(self.io_mapping_item)

    def setup_navigation_tree(self) -> None:
        self.io_mapping_item = QTreeWidgetItem(["IO Mapping"])
        self.program_item = QTreeWidgetItem(["Program"])
        self.main_program_item = QTreeWidgetItem(["Main Program"])
        self.program_item.addChild(self.main_program_item)

        self.navigation_tree.addTopLevelItem(self.io_mapping_item)
        self.navigation_tree.addTopLevelItem(self.program_item)
        self.program_item.setExpanded(True)

    def create_ladder_editor_page(self) -> QWidget:
        self.input_editor = QTextEdit()
        self.input_editor.setPlaceholderText(
            "Enter ladder logic (e.g., input1 & input2 -> output1)"
        )

        self.compile_button = QPushButton("Compile")
        self.compile_button.clicked.connect(self.compile_ladder)

        self.export_button = QPushButton("Export .ino")
        self.export_button.clicked.connect(self.export_ino)

        self.output_viewer = QTextEdit()
        self.output_viewer.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.input_editor)
        layout.addWidget(self.compile_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.output_viewer)

        page = QWidget()
        page.setLayout(layout)
        return page

    def create_io_mapping_page(self) -> QWidget:
        self.io_mapping_widget = IOMappingWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.io_mapping_widget)

        page = QWidget()
        page.setLayout(layout)
        return page

    def get_mapping(self) -> dict:
        return self.io_mapping_widget.get_mapping()

    def get_validation_mapping(self) -> list[dict]:
        return self.io_mapping_widget.get_validation_mapping()

    def change_page(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        if current is self.io_mapping_item:
            self.pages.setCurrentWidget(self.io_mapping_page)
        elif current is self.main_program_item:
            self.pages.setCurrentWidget(self.ladder_editor_page)

    def compile_ladder(self) -> None:
        try:
            ladder_code = self.input_editor.toPlainText()
            errors = validation(self.get_validation_mapping(), ladder_code)
            if errors:
                self.output_viewer.setPlainText("\n".join(errors))
                return

            st_code = ladder_to_st(ladder_code)
            c_code = compile_st_to_c(st_code)
            self.output_viewer.setPlainText(c_code)
        except Exception as error:
            self.output_viewer.setPlainText(f"Error: {error}")

    def export_ino(self) -> None:
        try:
            code = self.output_viewer.toPlainText()
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export .ino",
                "output.ino",
                "Arduino Sketch (*.ino);;All Files (*)",
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(code)
                self.output_viewer.append("\nFile saved successfully")
        except Exception as error:
            self.output_viewer.append(f"\nError: {error}")
