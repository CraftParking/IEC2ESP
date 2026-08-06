"""Controller type + WiFi settings + IO mapping.

IO mapping rows are fixed to the selected profile's pin list
(app/profiles/*.json 'pins' array) for pin-based profiles (ESP32, the XIAO
boards, CYD): no pin-number entry, no adding/removing rows - the board's
real pinout is the row set, and each row's Type choices are constrained to
that pin's declared capabilities. Custom has no fixed pin list (it's the
escape hatch for boards we don't have a profile for), so it keeps the old
free-form tag/pin/type table instead.

ControllerConfig also carries mqtt_enabled/ethernet_enabled/modbus_enabled,
but app.core.codegen.c_generator never reads them, so surfacing those
toggles would be inert."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.project import IOMappingEntry, Project

PHYSICAL_IO_TYPES = [
    "Digital Input", "Digital Output", "Analog Input", "Analog Output",
    "PWM Output", "UART TX", "UART RX",
]


class ControllerPanel(QWidget):
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

        controller_row = QHBoxLayout()
        controller_row.addWidget(QLabel("Controller:"))
        self.controller_combo = QComboBox()
        self.controller_combo.addItems(self.profile_manager.get_profile_names())
        self.controller_combo.setFixedWidth(160)
        self.controller_combo.currentTextChanged.connect(self._on_controller_changed)
        controller_row.addWidget(self.controller_combo)
        controller_row.addStretch()
        layout.addLayout(controller_row)

        wifi_row = QHBoxLayout()
        self.wifi_enabled = QCheckBox("Enable WiFi")
        self.wifi_enabled.toggled.connect(self._on_wifi_enabled_toggled)
        wifi_row.addWidget(self.wifi_enabled)

        wifi_row.addSpacing(15)
        wifi_row.addWidget(QLabel("Mode:"))
        self.wifi_mode = QComboBox()
        self.wifi_mode.addItems(["STA", "AP"])
        self.wifi_mode.setFixedWidth(80)
        self.wifi_mode.currentTextChanged.connect(lambda text: self._set_config("wifi_mode", text))
        wifi_row.addWidget(self.wifi_mode)

        wifi_row.addSpacing(15)
        wifi_row.addWidget(QLabel("SSID:"))
        self.wifi_ssid = QLineEdit()
        self.wifi_ssid.setFixedWidth(180)
        self.wifi_ssid.textChanged.connect(lambda text: self._set_config("wifi_ssid", text))
        wifi_row.addWidget(self.wifi_ssid)

        wifi_row.addSpacing(15)
        wifi_row.addWidget(QLabel("Password:"))
        self.wifi_password = QLineEdit()
        self.wifi_password.setFixedWidth(180)
        self.wifi_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.wifi_password.textChanged.connect(lambda text: self._set_config("wifi_password", text))
        wifi_row.addWidget(self.wifi_password)

        wifi_row.addStretch()
        layout.addLayout(wifi_row)

        layout.addWidget(QLabel("IO Mapping:"))
        self.io_table = QTableWidget(0, 4)
        self.io_table.setToolTip("Assign a tag to each pin you want to use.")
        self.io_table.verticalHeader().setVisible(False)
        self.io_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.io_table)

        add_row = QHBoxLayout()
        self.add_mapping_btn = QPushButton("Add Mapping")
        self.add_mapping_btn.clicked.connect(self._add_freeform_mapping)
        add_row.addWidget(self.add_mapping_btn)
        add_row.addStretch()
        layout.addLayout(add_row)

    def set_project(self, project: Project) -> None:
        self.project = project
        self.refresh()

    def _current_profile(self) -> dict | None:
        if self.project is None:
            return None
        return self.profile_manager.get_profile(self.project.controller_type)

    def _tag_choices(self) -> list[str]:
        if self.project is None:
            return []
        return [v.name for v in self.project.variables]

    def refresh(self) -> None:
        if self.project is None:
            return
        self.controller_combo.blockSignals(True)
        self.controller_combo.setCurrentText(self.project.controller_type)
        self.controller_combo.blockSignals(False)

        config = self.project.controller_config
        for widget, value in (
            (self.wifi_enabled, config.wifi_enabled),
            (self.wifi_mode, config.wifi_mode),
            (self.wifi_ssid, config.wifi_ssid),
            (self.wifi_password, config.wifi_password),
        ):
            widget.blockSignals(True)
            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(value)
            else:
                widget.setText(value)
            widget.blockSignals(False)

        self._update_wifi_fields_enabled()
        self._refresh_io_table()

    def _update_wifi_fields_enabled(self) -> None:
        enabled = self.wifi_enabled.isChecked()
        self.wifi_mode.setEnabled(enabled)
        self.wifi_ssid.setEnabled(enabled)
        self.wifi_password.setEnabled(enabled)

    def _on_controller_changed(self, name: str) -> None:
        if self.project is None or not name:
            return
        self.project.controller_type = name
        self.changed.emit()
        self._refresh_io_table()

    def _on_wifi_enabled_toggled(self, checked: bool) -> None:
        self._set_config("wifi_enabled", checked)
        self._update_wifi_fields_enabled()

    def _set_config(self, field_name: str, value) -> None:
        if self.project is None:
            return
        setattr(self.project.controller_config, field_name, value)
        self.changed.emit()

    # ---- IO mapping: fixed rows (pin-based profile) ----

    def _entry_for_pin(self, pin_number: int) -> IOMappingEntry | None:
        for entry in self.project.io_mapping:
            if entry.pin == pin_number:
                return entry
        return None

    def _refresh_io_table(self) -> None:
        if self.project is None:
            return
        profile = self._current_profile()
        pins = profile.get("pins") if profile else None

        self.io_table.clear()
        self.io_table.setRowCount(0)

        if pins:
            self.add_mapping_btn.setVisible(False)
            self.io_table.setColumnCount(4)
            self.io_table.setHorizontalHeaderLabels(["Pin", "Tag", "Type", "Pull-up"])
            header = self.io_table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            type_mapping = profile.get("type_mapping", {})
            for pin_def in pins:
                self._insert_fixed_pin_row(pin_def, type_mapping)
        else:
            self.add_mapping_btn.setVisible(True)
            self.io_table.setColumnCount(5)
            self.io_table.setHorizontalHeaderLabels(["Tag", "Pin", "Type", "Pull-up", ""])
            header = self.io_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.io_table.setColumnWidth(4, 32)
            for index, entry in enumerate(self.project.io_mapping):
                self._insert_freeform_row(index, entry)

    def _pin_allowed_types(self, pin_def: dict, type_mapping: dict) -> list[str]:
        allowed = [type_mapping.get(cap, cap) for cap in pin_def.get("capabilities", [])]
        allowed = [t for t in allowed if t in PHYSICAL_IO_TYPES]
        return allowed or list(PHYSICAL_IO_TYPES)

    def _insert_fixed_pin_row(self, pin_def: dict, type_mapping: dict) -> None:
        row = self.io_table.rowCount()
        self.io_table.insertRow(row)

        pin_number = pin_def["pin"]
        entry = self._entry_for_pin(pin_number)

        pin_item = QTableWidgetItem(pin_def.get("label", str(pin_number)))
        pin_item.setFlags(pin_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        tooltip_bits = []
        if pin_def.get("note"):
            tooltip_bits.append(pin_def["note"])
        if pin_def.get("flags"):
            tooltip_bits.append("Flags: " + ", ".join(pin_def["flags"]))
        if tooltip_bits:
            pin_item.setToolTip(" | ".join(tooltip_bits))
        self.io_table.setItem(row, 0, pin_item)

        allowed_types = self._pin_allowed_types(pin_def, type_mapping)
        pull_supported = "digital_in" in pin_def.get("capabilities", []) and "no_pull" not in pin_def.get("flags", [])

        type_combo = QComboBox()
        type_combo.addItems(allowed_types)
        if entry and entry.var_type in allowed_types:
            type_combo.setCurrentText(entry.var_type)
        type_combo.setEnabled(entry is not None)
        type_combo.currentTextChanged.connect(
            lambda text, pin=pin_number: self._on_fixed_field_changed(pin, "var_type", text)
        )
        self.io_table.setCellWidget(row, 2, type_combo)

        pullup_check = QCheckBox()
        pullup_check.setChecked(bool(entry and entry.pullup))
        pullup_check.setEnabled(pull_supported and entry is not None)
        pullup_check.toggled.connect(
            lambda checked, pin=pin_number: self._on_fixed_field_changed(pin, "pullup", checked)
        )
        self.io_table.setCellWidget(row, 3, pullup_check)

        tag_combo = QComboBox()
        tag_combo.setEditable(True)
        tag_combo.addItem("")
        tag_combo.addItems(self._tag_choices())
        tag_combo.setCurrentText(entry.tag if entry else "")
        tag_combo.currentTextChanged.connect(
            lambda text, pin=pin_number, tc=type_combo, pc=pullup_check, ps=pull_supported: (
                self._on_fixed_tag_changed(pin, text, tc, pc, ps)
            )
        )
        self.io_table.setCellWidget(row, 1, tag_combo)

    def _on_fixed_tag_changed(
        self, pin: int, text: str, type_combo: QComboBox, pullup_check: QCheckBox, pull_supported: bool
    ) -> None:
        if self.project is None:
            return
        entry = self._entry_for_pin(pin)
        text = text.strip()
        if not text:
            if entry is not None:
                self.project.io_mapping.remove(entry)
                self.changed.emit()
            type_combo.setEnabled(False)
            pullup_check.setEnabled(False)
            return
        if entry is None:
            entry = IOMappingEntry(tag=text, pin=pin, var_type=type_combo.currentText())
            self.project.io_mapping.append(entry)
        else:
            entry.tag = text
        type_combo.setEnabled(True)
        pullup_check.setEnabled(pull_supported)
        self.changed.emit()

    def _on_fixed_field_changed(self, pin: int, field_name: str, value) -> None:
        entry = self._entry_for_pin(pin)
        if entry is None:
            return
        setattr(entry, field_name, value)
        self.changed.emit()

    # ---- IO mapping: free-form rows (Custom profile, no fixed pin list) ----

    def _insert_freeform_row(self, index: int, entry: IOMappingEntry) -> None:
        row = self.io_table.rowCount()
        self.io_table.insertRow(row)

        tag_combo = QComboBox()
        tag_combo.setEditable(True)
        tag_combo.addItems(self._tag_choices())
        tag_combo.setCurrentText(entry.tag)
        tag_combo.currentTextChanged.connect(
            lambda text, idx=index: self._on_freeform_field_changed(idx, "tag", text)
        )
        self.io_table.setCellWidget(row, 0, tag_combo)

        pin_spin = QSpinBox()
        pin_spin.setRange(0, 255)
        pin_spin.setValue(entry.pin)
        pin_spin.valueChanged.connect(
            lambda value, idx=index: self._on_freeform_field_changed(idx, "pin", value)
        )
        self.io_table.setCellWidget(row, 1, pin_spin)

        type_combo = QComboBox()
        type_combo.addItems(PHYSICAL_IO_TYPES)
        type_combo.setCurrentText(entry.var_type)
        type_combo.currentTextChanged.connect(
            lambda text, idx=index: self._on_freeform_field_changed(idx, "var_type", text)
        )
        self.io_table.setCellWidget(row, 2, type_combo)

        pullup_check = QCheckBox()
        pullup_check.setChecked(entry.pullup)
        pullup_check.toggled.connect(
            lambda checked, idx=index: self._on_freeform_field_changed(idx, "pullup", checked)
        )
        self.io_table.setCellWidget(row, 3, pullup_check)

        remove_btn = QToolButton()
        remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        remove_btn.setToolTip("Delete mapping")
        remove_btn.clicked.connect(lambda _checked=False, idx=index: self._delete_freeform_mapping(idx))
        self.io_table.setCellWidget(row, 4, remove_btn)

    def _on_freeform_field_changed(self, index: int, field_name: str, value) -> None:
        if self.project is None or index >= len(self.project.io_mapping):
            return
        setattr(self.project.io_mapping[index], field_name, value)
        self.changed.emit()

    def _add_freeform_mapping(self) -> None:
        if self.project is None:
            return
        self.project.io_mapping.append(IOMappingEntry(tag="", pin=0, var_type="Digital Input"))
        self._refresh_io_table()
        self.changed.emit()

    def _delete_freeform_mapping(self, index: int) -> None:
        if self.project is None or index >= len(self.project.io_mapping):
            return
        del self.project.io_mapping[index]
        self._refresh_io_table()
        self.changed.emit()
