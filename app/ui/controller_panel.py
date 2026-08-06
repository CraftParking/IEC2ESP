"""Controller type + WiFi settings, mapped straight onto
app.core.controller_config.ControllerConfig. Only WiFi fields are exposed -
ControllerConfig also carries mqtt_enabled/ethernet_enabled/modbus_enabled,
but app.core.codegen.c_generator never reads them, so surfacing those
toggles would be inert."""

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from app.ui.project import Project


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
        layout.addStretch()

    def set_project(self, project: Project) -> None:
        self.project = project
        self.refresh()

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

    def _on_wifi_enabled_toggled(self, checked: bool) -> None:
        self._set_config("wifi_enabled", checked)
        self._update_wifi_fields_enabled()

    def _set_config(self, field_name: str, value) -> None:
        if self.project is None:
            return
        setattr(self.project.controller_config, field_name, value)
        self.changed.emit()
