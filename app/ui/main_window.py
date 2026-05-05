import json

from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QToolBar,
)

from app.core.compiler import compile_st_to_c
from app.core.ladder.ladder_to_st import ladder_to_st
from app.core.validation import validation
from app.core.profiles.profile_manager import ProfileManager, ProfileValidationError
from app.core.controller_config import ControllerConfig


class ControllerSelectionDialog(QDialog):
    """Dialog for selecting a controller profile."""
    
    def __init__(self, profile_manager, current_controller, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.current_controller = current_controller
        self.selected_controller = None
        self.setWindowTitle("Select Controller")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        
        # Label
        layout.addWidget(QLabel("Available Controllers:"))
        
        # List widget
        self.controller_list = QListWidget()
        self._populate_controller_list()
        self.controller_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.controller_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self._on_update_clicked)
        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.reject)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.exit_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_controller_list(self) -> None:
        """Populate the list with available controller profiles."""
        self.controller_list.clear()
        
        if self.profile_manager:
            profile_names = self.profile_manager.get_profile_names()
        else:
            profile_names = ["Custom", "ESP32"]
        
        for name in profile_names:
            item = QListWidgetItem(name)
            if name.lower() == self.current_controller:
                item.setSelected(True)
            self.controller_list.addItem(item)
    
    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on an item."""
        self.selected_controller = item.text()
        self.accept()
    
    def _on_update_clicked(self) -> None:
        """Handle Update button click."""
        current_item = self.controller_list.currentItem()
        if current_item:
            self.selected_controller = current_item.text()
            self.accept()
    
    def get_selected_controller(self) -> str:
        """Return the selected controller name."""
        return self.selected_controller


class ControllerConfigDialog(QDialog):
    """Dialog for configuring controller system features (WiFi, MQTT, etc.)."""
    
    def __init__(self, config: ControllerConfig, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowTitle("Controller Configuration")
        self.setMinimumSize(700, 500)

        main_layout = QHBoxLayout()

        # Left side - toolbar
        self.toolbar = QListWidget()
        self.toolbar.setFixedWidth(150)
        self.toolbar.addItem("WiFi")
        self.toolbar.addItem("MQTT")
        self.toolbar.addItem("Ethernet")
        self.toolbar.addItem("Modbus")
        self.toolbar.addItem("System")
        self.toolbar.currentRowChanged.connect(self._on_toolbar_changed)
        main_layout.addWidget(self.toolbar)

        # Right side - stacked widget
        self.stacked_widget = QStackedWidget()
        self._create_wifi_page()
        self._create_placeholder_pages()
        main_layout.addWidget(self.stacked_widget)

        self.setLayout(main_layout)
        
        # Add OK/Cancel buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)
        
        # Load current config into UI
        self._load_config()
    
    def _create_wifi_page(self) -> None:
        """Create WiFi configuration page."""
        page = QWidget()
        layout = QVBoxLayout()

        # Enable WiFi checkbox
        self.wifi_enable_checkbox = QCheckBox("Enable WiFi")
        self.wifi_enable_checkbox.toggled.connect(self._on_wifi_enable_toggled)
        layout.addWidget(self.wifi_enable_checkbox)

        layout.addSpacing(20)

        # SSID
        layout.addWidget(QLabel("SSID:"))
        self.wifi_ssid_input = QLineEdit()
        layout.addWidget(self.wifi_ssid_input)

        layout.addSpacing(10)

        # Password
        layout.addWidget(QLabel("Password:"))
        self.wifi_password_input = QLineEdit()
        self.wifi_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.wifi_password_input)

        layout.addSpacing(10)

        # Mode
        layout.addWidget(QLabel("Mode:"))
        self.wifi_mode_combo = QComboBox()
        self.wifi_mode_combo.addItems(["STA (Station)", "AP (Access Point)"])
        layout.addWidget(self.wifi_mode_combo)

        layout.addSpacing(20)

        # Warning about ADC2 pins
        warning_label = QLabel(
            "⚠️ Note: When WiFi is enabled, ADC2 pins (GPIO 0, 2, 4, 12-15, 25-27) "
            "may be unreliable for analog reads."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(warning_label)

        layout.addStretch()

        page.setLayout(layout)
        self.stacked_widget.addWidget(page)
    
    def _create_placeholder_pages(self) -> None:
        """Create placeholder pages for future features."""
        for _ in range(4):  # MQTT, Ethernet, Modbus, System
            page = QWidget()
            layout = QVBoxLayout()
            label = QLabel("This feature is not yet implemented.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            layout.addStretch()
            page.setLayout(layout)
            self.stacked_widget.addWidget(page)
    
    def _on_toolbar_changed(self, index: int) -> None:
        """Handle toolbar selection change."""
        self.stacked_widget.setCurrentIndex(index)
    
    def _on_wifi_enable_toggled(self, checked: bool) -> None:
        """Handle WiFi enable checkbox toggle."""
        self.wifi_ssid_input.setEnabled(checked)
        self.wifi_password_input.setEnabled(checked)
        self.wifi_mode_combo.setEnabled(checked)
    
    def _load_config(self) -> None:
        """Load current config into UI."""
        self.wifi_enable_checkbox.setChecked(self.config.wifi_enabled)
        self.wifi_ssid_input.setText(self.config.wifi_ssid)
        self.wifi_password_input.setText(self.config.wifi_password)
        
        # Set mode
        mode_index = 0 if self.config.wifi_mode == "STA" else 1
        self.wifi_mode_combo.setCurrentIndex(mode_index)
        
        # Update enabled state
        self._on_wifi_enable_toggled(self.config.wifi_enabled)
    
    def save_config(self) -> None:
        """Save UI values to config object."""
        self.config.wifi_enabled = self.wifi_enable_checkbox.isChecked()
        self.config.wifi_ssid = self.wifi_ssid_input.text()
        self.config.wifi_password = self.wifi_password_input.text()
        
        # Get mode
        mode_text = self.wifi_mode_combo.currentText()
        self.config.wifi_mode = "STA" if "STA" in mode_text else "AP"


class IOMappingWidget(QWidget):
    PIN_TYPES = ["Input", "Output", "Power", "Ground", "TX", "RX", "PWM", "Analog", "Reserved"]
    mapping_changed = pyqtSignal()

    def __init__(self, profile_manager=None, main_window=None) -> None:
        super().__init__()
        self.rows = []
        self.controller_type = "custom"
        self.profile_manager = profile_manager
        self.main_window = main_window
        self.controller_config = ControllerConfig()

        self.controller_button = QPushButton("Change Controller")
        self.controller_button.clicked.connect(self.open_controller_dialog)
        
        self.controller_config_button = QPushButton("Controller Configuration")
        self.controller_config_button.clicked.connect(self.open_controller_config_dialog)
        
        self.controller_label = QLabel("Custom")
        font = QFont()
        font.setBold(True)
        self.controller_label.setFont(font)

        self.pin_count = QSpinBox()
        self.pin_count.setRange(1, 100)
        self.pin_count.setValue(30)
        self.pin_count.valueChanged.connect(lambda: self.apply_custom_profile(self.pin_count.value()))

        controls = QHBoxLayout()
        controls.addWidget(self.controller_label)
        controls.addWidget(self.controller_button)
        controls.addWidget(self.controller_config_button)
        controls.addSpacing(20)
        controls.addWidget(QLabel("Number of Pins"))
        controls.addWidget(self.pin_count)
        controls.addStretch()

        self.grid = QGridLayout()
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setColumnStretch(0, 0)
        self.grid.setColumnStretch(1, 3)
        self.grid.setColumnStretch(2, 1)
        self.grid.setColumnStretch(3, 0)

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
        layout.addWidget(scroll_area)
        self.setLayout(layout)

        self.apply_custom_profile(self.pin_count.value())

    def apply_custom_profile(self, pin_count: int) -> None:
        self.clear_grid()
        self.rows = []

        from PyQt6.QtGui import QFont
        font = QFont()
        font.setBold(True)

        pin_header = QLabel("Pin")
        pin_header.setFont(font)
        tag_header = QLabel("Tag Name")
        tag_header.setFont(font)
        type_header = QLabel("Type")
        type_header.setFont(font)
        pull_header = QLabel("Pull")
        pull_header.setFont(font)

        self.grid.addWidget(pin_header, 0, 0)
        self.grid.addWidget(tag_header, 0, 1)
        self.grid.addWidget(type_header, 0, 2)
        self.grid.addWidget(pull_header, 0, 3)

        # Get Custom profile from profile manager or use fallback
        if self.profile_manager:
            custom_profile = self.profile_manager.get_profile("Custom")
            allowed_types = custom_profile.get("allowed_types", self.PIN_TYPES) if custom_profile else self.PIN_TYPES
            pull_support = custom_profile.get("pull_support", True) if custom_profile else True
        else:
            allowed_types = self.PIN_TYPES
            pull_support = True

        for row in range(pin_count):
            pin_number = row
            pin_label = QLabel(f"GPIO {pin_number}")
            tag_input = QLineEdit()
            pin_type = QComboBox()
            pin_type.addItems(allowed_types)
            pull_combo = QComboBox()
            pull_combo.addItems(["None", "Pull-Up", "Pull-Down"])
            pull_combo.setCurrentText("None")
            
            tag_input.setEnabled(True)
            pull_combo.setEnabled(pull_support)
            
            tag_input.textChanged.connect(self.mapping_changed.emit)
            pin_type.currentTextChanged.connect(
                lambda selected_type, field=tag_input, combo=pull_combo: self.update_row_state(
                    field,
                    combo,
                    selected_type,
                )
            )
            pin_type.currentTextChanged.connect(self.mapping_changed.emit)
            pull_combo.currentTextChanged.connect(self.mapping_changed.emit)
            self.update_row_state(tag_input, pull_combo, pin_type.currentText())

            self.grid.addWidget(pin_label, row + 1, 0, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(tag_input, row + 1, 1, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(pin_type, row + 1, 2, alignment=Qt.AlignmentFlag.AlignTop)
            self.grid.addWidget(pull_combo, row + 1, 3, alignment=Qt.AlignmentFlag.AlignTop)
            self.rows.append(
                {
                    "pin": pin_number,
                    "tag_input": tag_input,
                    "type_combo": pin_type,
                    "pull_combo": pull_combo,
                }
            )

    def clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.rows = []

    def update_row_state(self, tag_input: QLineEdit, pull_combo: QComboBox, pin_type: str, profile_data: dict = None) -> None:
        """Update row state based on pin type and profile constraints."""
        if profile_data is None:
            # Fallback for custom profile
            is_logic_pin = pin_type in ("Input", "Output")
            tag_input.setEnabled(is_logic_pin)
            if not is_logic_pin:
                tag_input.clear()

            is_input = pin_type == "Input"
            pull_combo.setEnabled(is_input)
            if not is_input:
                pull_combo.setCurrentText("None")
            return

        # Capability-based enforcement
        flags = profile_data.get("flags", [])
        capabilities = profile_data.get("capabilities", [])
        
        is_reserved = "reserved" in flags or len(capabilities) == 0
        is_input_only = "input_only" in flags
        has_no_pull = "no_pull" in flags
        
        # Enable tag input for all logic types (any type with Input or Output in the name)
        type_lower = pin_type.lower()
        is_logic_type = "input" in type_lower or "output" in type_lower
        tag_input.setEnabled(is_logic_type and not is_reserved)
        if not is_logic_type or is_reserved:
            tag_input.clear()
        
        # Enable pull combo ONLY for Digital Input when:
        # 1. Pin is not input-only (or if it is, still allow digital input)
        # 2. Pin supports pull (no no_pull flag)
        # 3. Pin type is Digital Input specifically
        # 4. Pin is not reserved
        should_enable_pull = (
            pin_type == "Digital Input" and 
            not has_no_pull and 
            not is_reserved
        )
        
        pull_combo.setEnabled(should_enable_pull)
        
        if not should_enable_pull:
            pull_combo.setCurrentText("None")
            if has_no_pull:
                # If pin doesn't support pull at all, only show "None"
                pull_combo.clear()
                pull_combo.addItems(["None"])

    def open_controller_dialog(self) -> None:
        """Open dialog to select controller profile."""
        dialog = ControllerSelectionDialog(self.profile_manager, self.controller_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_controller = dialog.get_selected_controller()
            if selected_controller:
                # Temporary workaround: apply profile twice to ensure UI updates
                self.on_controller_changed(selected_controller)
                # Apply again after a short delay to force UI refresh
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, lambda: self.on_controller_changed(selected_controller))
    
    def open_controller_config_dialog(self) -> None:
        """Open dialog to configure controller system features."""
        dialog = ControllerConfigDialog(self.controller_config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_config()
            self.mapping_changed.emit()

    def on_controller_changed(self, controller: str) -> None:
        old_controller_type = self.controller_type
        self.controller_type = controller.lower()
        
        # Update label text
        self.controller_label.setText(controller)
        
        # Update navigation tree item
        if hasattr(self, 'main_window'):
            self.main_window.update_controller_tree_item(controller)
        
        preserved_tags = {}
        if old_controller_type == "custom" and self.controller_type == "esp32":
            for row in self.rows:
                pin = row["pin"]
                tag = row["tag_input"].text().strip()
                if tag:
                    preserved_tags[pin] = tag
        
        try:
            if self.profile_manager:
                # Try case-insensitive lookup
                profile = self.profile_manager.get_profile(controller)
                if profile is None:
                    # Try with different case
                    for profile_name in self.profile_manager.get_profile_names():
                        if profile_name.lower() == controller.lower():
                            profile = self.profile_manager.get_profile(profile_name)
                            break
                if profile:
                    self.apply_profile(profile, preserved_tags)
                else:
                    # Fallback to Custom if profile not found
                    self.pin_count.setEnabled(True)
                    self.apply_custom_profile(self.pin_count.value())
            else:
                # Fallback to Custom if no profile manager
                self.pin_count.setEnabled(True)
                self.apply_custom_profile(self.pin_count.value())
        except Exception as e:
            # Safe fallback to Custom profile on any error
            self.pin_count.setEnabled(True)
            self.apply_custom_profile(self.pin_count.value())
        
        self.mapping_changed.emit()

    def apply_profile(self, profile: dict, preserved_tags: dict = None) -> None:
        """Apply a profile from the profile manager."""
        
        if "pins" in profile:
            # Pin-based profile (like ESP32)
            self.clear_grid()
            pin_count = profile["pin_count"]
            
            # Get type mapping if available
            type_mapping = profile.get("type_mapping", {})
            
            from PyQt6.QtGui import QFont
            font = QFont()
            font.setBold(True)

            pin_header = QLabel("Pin")
            pin_header.setFont(font)
            tag_header = QLabel("Tag Name")
            tag_header.setFont(font)
            type_header = QLabel("Type")
            type_header.setFont(font)
            pull_header = QLabel("Pull")
            pull_header.setFont(font)

            self.grid.addWidget(pin_header, 0, 0)
            self.grid.addWidget(tag_header, 0, 1)
            self.grid.addWidget(type_header, 0, 2)
            self.grid.addWidget(pull_header, 0, 3)
            
            pin_map = {pin["pin"]: pin for pin in profile["pins"]}
            
            for row in range(pin_count):
                pin_number = row
                pin_label = QLabel(f"GPIO {pin_number}")
                tag_input = QLineEdit()
                pin_type = QComboBox()
                pull_combo = QComboBox()
                pull_combo.addItems(["None", "Pull-Up", "Pull-Down"])
                pull_combo.setCurrentText("None")
                
                # Get profile data for this pin, or use default
                if pin_number in pin_map:
                    profile_data = pin_map[pin_number]
                else:
                    # Default for pins not in profile (should be rare)
                    profile_data = {
                        "tag": "",
                        "pull": "none",
                        "capabilities": ["digital_in", "digital_out"],
                        "flags": []
                    }
                
                # Set tooltip if note exists
                if profile_data.get("note"):
                    pin_label.setToolTip(profile_data["note"])
                    tag_input.setToolTip(profile_data["note"])
                    pin_type.setToolTip(profile_data["note"])
                    pull_combo.setToolTip(profile_data["note"])
                
                # Derive allowed types from capabilities
                capabilities = profile_data.get("capabilities", [])
                flags = profile_data.get("flags", [])
                
                # Map capabilities to display names
                allowed_types = []
                for cap in capabilities:
                    display_name = type_mapping.get(cap, cap.replace("_", " ").title())
                    allowed_types.append(display_name)
                
                # If no capabilities, it's reserved
                is_reserved = "reserved" in flags or len(capabilities) == 0
                is_input_only = "input_only" in flags
                has_no_pull = "no_pull" in flags
                
                # Add types to dropdown
                if allowed_types:
                    pin_type.addItems(allowed_types)
                    # Set default to first capability
                    if allowed_types:
                        pin_type.setCurrentText(allowed_types[0])
                else:
                    pin_type.addItem("Reserved")
                    pin_type.setEnabled(False)
                
                # Determine if single type (locked)
                is_single_type = len(allowed_types) == 1
                
                if is_reserved or is_single_type:
                    pin_type.setEnabled(False)
                    tag_input.setEnabled(False)
                    pull_combo.setEnabled(False)
                else:
                    tag_input.setEnabled(True)
                    # Pull combo will be managed by update_row_state based on type
                
                tag_input.setText(profile_data.get("tag", ""))
                pull_combo.setCurrentText(profile_data.get("pull", "none").capitalize() if profile_data.get("pull", "none") != "none" else "None")
                
                tag_input.textChanged.connect(self.mapping_changed.emit)
                pin_type.currentTextChanged.connect(
                    lambda selected_type, field=tag_input, combo=pull_combo, data=profile_data: self.update_row_state(
                        field,
                        combo,
                        selected_type,
                        data,
                    )
                )
                pin_type.currentTextChanged.connect(self.mapping_changed.emit)
                pull_combo.currentTextChanged.connect(self.mapping_changed.emit)
                self.update_row_state(tag_input, pull_combo, pin_type.currentText(), profile_data)
                
                self.grid.addWidget(pin_label, row + 1, 0, alignment=Qt.AlignmentFlag.AlignTop)
                self.grid.addWidget(tag_input, row + 1, 1, alignment=Qt.AlignmentFlag.AlignTop)
                self.grid.addWidget(pin_type, row + 1, 2, alignment=Qt.AlignmentFlag.AlignTop)
                self.grid.addWidget(pull_combo, row + 1, 3, alignment=Qt.AlignmentFlag.AlignTop)
                self.rows.append(
                    {
                        "pin": pin_number,
                        "tag_input": tag_input,
                        "type_combo": pin_type,
                        "pull_combo": pull_combo,
                        "profile_data": profile_data,
                        "capabilities": capabilities,
                        "flags": flags,
                    }
                )
            
            self.pin_count.setEnabled(False)
            self.pin_count.setValue(pin_count)
            
            if preserved_tags:
                for row in self.rows:
                    pin = row["pin"]
                    if pin in preserved_tags:
                        flags = row.get("flags", [])
                        capabilities = row.get("capabilities", [])
                        is_reserved = "reserved" in flags or len(capabilities) == 0
                        is_single_type = len(capabilities) == 1
                        if not is_reserved and not is_single_type:
                            row["tag_input"].setText(preserved_tags[pin])
            
            # Force immediate layout recalculation
            self.grid.layout().invalidate()
            self.grid.layout().activate()
            self.updateGeometry()
            self.update()
            self.repaint()
            
            # Propagate update up the widget hierarchy
            parent = self.parentWidget()
            while parent:
                parent.update()
                parent.repaint()
                parent = parent.parentWidget()
        else:
            # Simple profile (like Custom)
            self.pin_count.setEnabled(True)
            self.apply_custom_profile(self.pin_count.value())

    def get_mapping(self) -> dict:
        mapping = {}

        for row in self.rows:
            pin_type = row["type_combo"].currentText()
            tag_name = row["tag_input"].text().strip()

            # Check if it's a logic type (any type with Input or Output in the name)
            is_logic_type = "Input" in pin_type or "Output" in pin_type
            
            if is_logic_type and tag_name:
                pull_text = row["pull_combo"].currentText()
                pull_state = "none"
                if pull_text == "Pull-Up":
                    pull_state = "up"
                elif pull_text == "Pull-Down":
                    pull_state = "down"
                
                # Normalize type: "Digital Input" -> "input", "UART TX" -> "input"
                type_lower = pin_type.lower()
                if "input" in type_lower:
                    normalized_type = "input"
                elif "output" in type_lower:
                    normalized_type = "output"
                else:
                    normalized_type = type_lower
                
                mapping[tag_name] = {
                    "pin": row["pin"],
                    "type": normalized_type,
                    "pull": pull_state if "input" in type_lower else "none",
                }

        return mapping

    def get_validation_mapping(self) -> list[dict]:
        return [
            {
                "pin": row["pin"],
                "tag": row["tag_input"].text(),
                "type": row["type_combo"].currentText(),
                "pull": row["pull_combo"].currentText().lower().replace("-", ""),
            }
            for row in self.rows
            if row["type_combo"].currentText() != "Reserved" and row["tag_input"].text().strip()
        ]


class CodePreviewDialog(QDialog):
    def __init__(self, st_code: str, c_code: str, parent=None) -> None:
        super().__init__(parent)
        self.st_code = st_code
        self.c_code = c_code
        self.setWindowTitle("Code Preview")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.show_st_button = QPushButton("Show ST")
        self.show_st_button.setCheckable(True)
        self.show_st_button.clicked.connect(self.show_st)
        top_layout.addWidget(self.show_st_button)

        self.show_c_button = QPushButton("Show C")
        self.show_c_button.setCheckable(True)
        self.show_c_button.setChecked(True)
        self.show_c_button.clicked.connect(self.show_c)
        top_layout.addWidget(self.show_c_button)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        self.code_viewer = QTextEdit()
        self.code_viewer.setReadOnly(True)
        self.code_viewer.setPlainText(self.c_code)
        layout.addWidget(self.code_viewer)

        bottom_layout = QHBoxLayout()
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_code)
        bottom_layout.addWidget(copy_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        bottom_layout.addWidget(close_button)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)

    def show_st(self) -> None:
        self.show_st_button.setChecked(True)
        self.show_c_button.setChecked(False)
        self.code_viewer.setPlainText(self.st_code)

    def show_c(self) -> None:
        self.show_c_button.setChecked(True)
        self.show_st_button.setChecked(False)
        self.code_viewer.setPlainText(self.c_code)

    def copy_code(self) -> None:
        from PyQt6.QtGui import QClipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.code_viewer.toPlainText())


class ValidationErrorsDialog(QDialog):
    def __init__(self, errors: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validation Errors")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout()

        label = QLabel("Errors found during validation:")
        layout.addWidget(label)

        self.error_viewer = QTextEdit()
        self.error_viewer.setReadOnly(True)
        self.error_viewer.setPlainText("\n".join(errors))
        layout.addWidget(self.error_viewer)

        bottom_layout = QHBoxLayout()
        copy_button = QPushButton("Copy All")
        copy_button.clicked.connect(self.copy_errors)
        bottom_layout.addWidget(copy_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        bottom_layout.addWidget(close_button)

        layout.addLayout(bottom_layout)
        self.setLayout(layout)

    def copy_errors(self) -> None:
        from PyQt6.QtGui import QClipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_viewer.toPlainText())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IEC2ESP Ladder Compiler")
        self.setMinimumSize(900, 700)
        self.current_file_path = None
        self.compiled_code = None
        self.has_main_program = False
        self.is_modified = False

        import os
        profiles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "profiles"))
        self.profile_manager = ProfileManager(profiles_dir)

        self.create_menu_bar()

        self.update_program_creation_options()

        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderHidden(True)
        self.navigation_tree.currentItemChanged.connect(self.change_page)
        self.setup_navigation_tree()

        self.pages = QStackedWidget()
        self.io_mapping_page = self.create_io_mapping_page()
        self.ladder_editor_page = self.create_ladder_editor_page()
        self.placeholder_page = self.create_placeholder_page()
        self.pages.addWidget(self.io_mapping_page)
        self.pages.addWidget(self.ladder_editor_page)
        self.pages.addWidget(self.placeholder_page)

        splitter = QSplitter()
        splitter.addWidget(self.navigation_tree)
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        self.setCentralWidget(splitter)
        self.navigation_tree.setCurrentItem(self.controller_item)
        
        self.log("Application started", "INFO")

    def log(self, message: str, level: str = "INFO") -> None:
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        color = "black"
        if level == "SUCCESS":
            color = "green"
        elif level == "ERROR":
            color = "red"
        
        self.log_viewer.append(f'<span style="color:{color}">{log_entry}</span>')
        
        cursor = self.log_viewer.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_viewer.setTextCursor(cursor)
        self.log_viewer.ensureCursorVisible()

    def on_content_changed(self) -> None:
        self.is_modified = True
        self.update_window_title()

    def update_window_title(self) -> None:
        if self.is_modified:
            self.setWindowTitle("IEC2ESP Ladder Compiler *")
        else:
            self.setWindowTitle("IEC2ESP Ladder Compiler")

    def check_unsaved_changes(self) -> bool:
        if not self.is_modified:
            return True
        
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. What would you like to do?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        
        if reply == QMessageBox.StandardButton.Save:
            if self.current_file_path:
                self._save_to_file(self.current_file_path)
                return True
            else:
                self.save_project_as()
                return not self.is_modified
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else:
            return False

    def show_context_menu(self, position) -> None:
        item = self.navigation_tree.itemAt(position)
        if item == self.program_item and not self.has_main_program:
            menu = QMenu(self)
            add_program_action = QAction("Add Main Program", self)
            add_program_action.triggered.connect(self.create_main_program)
            menu.addAction(add_program_action)
            menu.exec(self.navigation_tree.mapToGlobal(position))
        elif item == self.main_program_item:
            menu = QMenu(self)
            close_action = QAction("Close", self)
            close_action.triggered.connect(lambda: self.change_page(self.program_item))
            menu.addAction(close_action)
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_main_program)
            menu.addAction(delete_action)
            menu.exec(self.navigation_tree.mapToGlobal(position))

    def create_main_program(self) -> None:
        if self.has_main_program:
            return
        
        self.main_program_item = QTreeWidgetItem(["Main Program"])
        self.program_item.addChild(self.main_program_item)
        self.program_item.setExpanded(True)
        self.has_main_program = True
        
        self.update_program_creation_options()
        self.navigation_tree.setCurrentItem(self.main_program_item)
        self.log("Main Program created", "INFO")

    def update_program_creation_options(self) -> None:
        if self.has_main_program:
            self.new_program_action.setEnabled(False)
        else:
            self.new_program_action.setEnabled(True)

    def delete_main_program(self) -> None:
        if not self.has_main_program:
            return
        
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. What would you like to do?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.save_project()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        reply = QMessageBox.question(
            self,
            "Delete Program",
            "Are you sure you want to delete the Main Program?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.main_program_item:
                self.program_item.removeChild(self.main_program_item)
                self.main_program_item = None
            
            self.has_main_program = False
            self.update_program_creation_options()
            
            self.input_editor.clear()
            self.input_editor.setPlaceholderText("No program available. Create a new Main Program.")
            
            self.log("Main Program deleted", "INFO")

    def import_profile(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Controller Profile",
            "",
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        success, error_msg, profile = self.profile_manager.import_profile(filepath)
        
        if success:
            profile_name = profile.get("name", "Imported Profile")
            self.log(f"Profile '{profile_name}' imported successfully", "INFO")
        else:
            QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import profile:\n{error_msg}"
            )
            self.log(f"Profile import failed: {error_msg}", "ERROR")

    def setup_navigation_tree(self) -> None:
        self.controller_item = QTreeWidgetItem(["Controller [Custom]"])
        self.program_item = QTreeWidgetItem(["Program"])
        self.main_program_item = None

        self.navigation_tree.addTopLevelItem(self.controller_item)
        self.navigation_tree.addTopLevelItem(self.program_item)
        self.program_item.setExpanded(True)
        
        self.navigation_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.navigation_tree.customContextMenuRequested.connect(self.show_context_menu)

    def create_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        new_menu = file_menu.addMenu("&New")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        new_menu.addAction(new_action)

        new_program_action = QAction("&Main Program", self)
        new_program_action.triggered.connect(self.create_main_program)
        self.new_program_action = new_program_action
        new_menu.addAction(new_program_action)

        file_menu.addSeparator()

        open_action = QAction("&Open Project", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("&Tools")

        compile_action = QAction("&Compile", self)
        compile_action.setShortcut(QKeySequence("Ctrl+R"))
        compile_action.triggered.connect(self.compile_ladder)
        tools_menu.addAction(compile_action)

        convert_action = QAction("&Convert (Ladder → ST / C)", self)
        convert_action.triggered.connect(self.convert_ladder)
        tools_menu.addAction(convert_action)

        export_action = QAction("&Export .ino", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export_ino)
        tools_menu.addAction(export_action)

        controller_menu = menubar.addMenu("&Controller")

        import_profile_action = QAction("&Import Profile", self)
        import_profile_action.triggered.connect(self.import_profile)
        controller_menu.addAction(import_profile_action)

    def create_ladder_editor_page(self) -> QWidget:
        self.input_editor = QTextEdit()
        self.input_editor.setPlaceholderText(
            "Enter ladder logic (e.g., input1 & input2 -> output1)"
        )
        self.input_editor.textChanged.connect(self.on_content_changed)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.input_editor)
        splitter.addWidget(self.log_viewer)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout()
        layout.addWidget(splitter)

        page = QWidget()
        page.setLayout(layout)
        return page

    def create_placeholder_page(self) -> QWidget:
        label = QLabel("Create a program to begin")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; color: gray;")

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addStretch()

        page = QWidget()
        page.setLayout(layout)
        return page

    def create_io_mapping_page(self) -> QWidget:
        self.io_mapping_widget = IOMappingWidget(self.profile_manager, self)
        self.io_mapping_widget.mapping_changed.connect(self.on_content_changed)
        layout = QVBoxLayout()
        layout.addWidget(self.io_mapping_widget)

        page = QWidget()
        page.setLayout(layout)
        return page

    def get_mapping(self) -> dict:
        return self.io_mapping_widget.get_mapping()

    def get_validation_mapping(self) -> list[dict]:
        return self.io_mapping_widget.get_validation_mapping()

    def update_controller_tree_item(self, controller: str) -> None:
        """Update the controller tree item with the current controller name."""
        if hasattr(self, 'controller_item'):
            # Smart truncation with ellipsis if name is too long
            max_length = 20
            display_name = controller
            if len(controller) > max_length:
                display_name = controller[:max_length - 3] + "..."
            self.controller_item.setText(0, f"Controller [{display_name}]")

    def change_page(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        if current is self.controller_item:
            self.pages.setCurrentWidget(self.io_mapping_page)
            # Force grid refresh when controller page becomes visible
            if hasattr(self, 'io_mapping_widget'):
                self.io_mapping_widget.setVisible(True)
                self.io_mapping_widget.grid.layout().invalidate()
                self.io_mapping_widget.grid.layout().activate()
                self.io_mapping_widget.updateGeometry()
        elif current is self.program_item:
            if self.has_main_program:
                self.pages.setCurrentWidget(self.ladder_editor_page)
            else:
                self.pages.setCurrentWidget(self.placeholder_page)
        elif current is self.main_program_item:
            self.pages.setCurrentWidget(self.ladder_editor_page)

    def compile_ladder(self) -> None:
        try:
            self.log("Compilation started", "INFO")
            ladder_code = self.input_editor.toPlainText()
            errors = validation(self.get_validation_mapping(), ladder_code)
            if errors:
                self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                dialog = ValidationErrorsDialog(errors, self)
                dialog.exec()
                return

            st_code = ladder_to_st(ladder_code)
            controller_config_dict = self.io_mapping_widget.controller_config.to_dict()
            c_code = compile_st_to_c(st_code, self.get_mapping(), controller_config_dict)
            self.compiled_code = c_code
            self.log("Compilation completed successfully", "SUCCESS")
        except Exception as error:
            self.log(f"Compilation error: {error}", "ERROR")

    def convert_ladder(self) -> None:
        try:
            self.log("Conversion started", "INFO")
            ladder_code = self.input_editor.toPlainText()
            errors = validation(self.get_validation_mapping(), ladder_code)
            if errors:
                self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                dialog = ValidationErrorsDialog(errors, self)
                dialog.exec()
                return

            st_code = ladder_to_st(ladder_code)
            controller_config_dict = self.io_mapping_widget.controller_config.to_dict()
            c_code = compile_st_to_c(st_code, self.get_mapping(), controller_config_dict)

            dialog = CodePreviewDialog(st_code, c_code, self)
            dialog.exec()
            self.log("Conversion completed successfully", "SUCCESS")
        except Exception as error:
            self.log(f"Conversion error: {error}", "ERROR")
            QMessageBox.critical(self, "Error", f"Conversion failed: {error}")

    def export_ino(self) -> None:
        try:
            self.log("Export .ino started", "INFO")
            code = self.compiled_code
            if not code:
                self.log("No compiled code to export", "ERROR")
                QMessageBox.warning(self, "Warning", "No compiled code to export. Please compile first.")
                return
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export .ino",
                "output.ino",
                "Arduino Sketch (*.ino);;All Files (*)",
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(code)
                self.log(f"Exported to {file_path}", "SUCCESS")
        except Exception as error:
            self.log(f"Export error: {error}", "ERROR")

    def new_project(self) -> None:
        if not self.check_unsaved_changes():
            return
        self.log("New project created", "INFO")
        self.input_editor.clear()
        self.compiled_code = None
        self.io_mapping_widget.controller_combo.setCurrentText("Custom")
        self.io_mapping_widget.pin_count.setValue(30)
        self.current_file_path = None
        self.is_modified = False
        self.update_window_title()
        
        if self.main_program_item:
            self.program_item.removeChild(self.main_program_item)
            self.main_program_item = None
        self.has_main_program = False
        self.update_program_creation_options()

    def save_project(self) -> None:
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            self.save_project_as()

    def save_project_as(self) -> None:
        program_text = self.input_editor.toPlainText()
        is_ladder = "->" in program_text or "&" in program_text or "|" in program_text
        
        if is_ladder:
            default_ext = ".ladesp"
            filter_str = "Ladder ESP Project (*.ladesp);;All Files (*)"
        else:
            default_ext = ".stesp"
            filter_str = "Structured Text ESP Project (*.stesp);;All Files (*)"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project",
            f"project{default_ext}",
            filter_str,
        )
        
        if file_path:
            self.current_file_path = file_path
            self._save_to_file(file_path)

    def _save_to_file(self, file_path: str) -> None:
        try:
            self.log(f"Saving project to {file_path}", "INFO")
            program_text = self.input_editor.toPlainText()
            is_ladder = "->" in program_text or "&" in program_text or "|" in program_text
            
            pins_data = []
            for row in self.io_mapping_widget.rows:
                pin_type = row["type_combo"].currentText()
                tag_name = row["tag_input"].text().strip()
                pins_data.append({
                    "pin": row["pin"],
                    "tag": tag_name,
                    "type": pin_type.lower(),
                    "pullup": row["pullup_checkbox"].isChecked() if pin_type == "Input" else False,
                })
            
            project_data = {
                "type": "ladder" if is_ladder else "st",
                "controller": self.io_mapping_widget.controller_type,
                "pin_count": self.io_mapping_widget.pin_count.value(),
                "has_main_program": self.has_main_program,
                "pins": pins_data,
                "program": program_text,
            }
            
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(project_data, file, indent=2)
            
            self.log("Project saved successfully", "SUCCESS")
            QMessageBox.information(self, "Success", "Project saved successfully!")
            self.is_modified = False
            self.update_window_title()
        except Exception as error:
            self.log(f"Save error: {error}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to save project: {error}")

    def open_project(self) -> None:
        if not self.check_unsaved_changes():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "IEC2ESP Project (*.ladesp *.stesp);;All Files (*)",
        )
        
        if file_path:
            self._load_from_file(file_path)

    def _load_from_file(self, file_path: str) -> None:
        try:
            self.log(f"Loading project from {file_path}", "INFO")
            with open(file_path, "r", encoding="utf-8") as file:
                project_data = json.load(file)
            
            if not isinstance(project_data, dict):
                raise ValueError("Invalid project file format")
            
            if "type" not in project_data or "pins" not in project_data or "program" not in project_data:
                raise ValueError("Missing required fields in project file")
            
            self.input_editor.setPlainText(project_data["program"])
            self.compiled_code = None
            
            has_main_program = project_data.get("has_main_program", False)
            if has_main_program and not self.has_main_program:
                self.create_main_program()
            elif not has_main_program and self.has_main_program:
                if self.main_program_item:
                    self.program_item.removeChild(self.main_program_item)
                    self.main_program_item = None
                self.has_main_program = False
                self.update_program_creation_options()
            
            controller_type = project_data.get("controller", "custom")
            self.io_mapping_widget.on_controller_changed(controller_type.capitalize())
            
            pin_count = project_data.get("pin_count", 30)
            self.io_mapping_widget.pin_count.setValue(pin_count)
            
            self.populate_io_mapping(project_data["pins"])
            
            self.current_file_path = file_path
            self.log("Project loaded successfully", "SUCCESS")
            QMessageBox.information(self, "Success", "Project loaded successfully!")
            self.is_modified = False
            self.update_window_title()
        except json.JSONDecodeError:
            self.log("Invalid JSON file format", "ERROR")
            QMessageBox.critical(self, "Error", "Invalid JSON file format")
        except Exception as error:
            self.log(f"Load error: {error}", "ERROR")
            QMessageBox.critical(self, "Error", f"Failed to load project: {error}")

    def closeEvent(self, event) -> None:
        if self.check_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    def populate_io_mapping(self, pins_data: list) -> None:
        for pin_data in pins_data:
            pin_number = pin_data.get("pin")
            tag_name = pin_data.get("tag", "")
            pin_type = pin_data.get("type", "")
            pull = pin_data.get("pull", "none")
            
            if pin_number < len(self.io_mapping_widget.rows):
                row = self.io_mapping_widget.rows[pin_number]
                
                type_index = row["type_combo"].findText(pin_type.capitalize())
                if type_index >= 0:
                    row["type_combo"].setCurrentIndex(type_index)
                
                row["tag_input"].setText(tag_name)
                
                # Set pull dropdown
                if pull == "up":
                    row["pull_combo"].setCurrentText("Pull-Up")
                elif pull == "down":
                    row["pull_combo"].setCurrentText("Pull-Down")
                else:
                    row["pull_combo"].setCurrentText("None")
