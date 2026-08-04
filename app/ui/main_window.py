import json

from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QPushButton, QLabel, QFrame, QDialog, QLineEdit, QMenu, QStyle,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox, QComboBox,
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
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


class NewProgramDialog(QDialog):
    """Dialog for creating a new main program with language selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.program_name = ""
        self.selected_language = "LAD"  # Default to LAD

        self.setWindowTitle("New Main Program")
        self.setMinimumSize(400, 250)

        layout = QVBoxLayout()

        # Program name
        layout.addWidget(QLabel("Program Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter program name (e.g., MainProgram)")
        layout.addWidget(self.name_input)

        layout.addSpacing(20)

        # Language selection
        layout.addWidget(QLabel("Programming Language:"))
        
        self.lad_radio = QRadioButton("LAD - Ladder Diagram")
        self.lad_radio.setChecked(True)  # Default to LAD
        self.lad_radio.toggled.connect(self._on_language_changed)
        layout.addWidget(self.lad_radio)
        
        self.stl_radio = QRadioButton("STL - Statement List")
        self.stl_radio.toggled.connect(self._on_language_changed)
        layout.addWidget(self.stl_radio)

        layout.addSpacing(20)

        # Description
        self.description_label = QLabel(
            "LAD: Graphical ladder logic representation\n"
            "STL: Text-based structured text representation"
        )
        self.description_label.setStyleSheet("color: gray;")
        layout.addWidget(self.description_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("Create")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
    
    def _on_language_changed(self) -> None:
        """Handle language radio button change."""
        if self.lad_radio.isChecked():
            self.selected_language = "LAD"
        else:
            self.selected_language = "STL"
    
    def get_program_name(self) -> str:
        """Return the program name."""
        return self.program_name
    
    def get_selected_language(self) -> str:
        """Return the selected language."""
        return self.selected_language
    
    def accept(self) -> None:
        """Validate and accept the dialog."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a program name.")
            return
        self.program_name = name
        super().accept()


class ProgramPropertiesDialog(QDialog):
    """Dialog for editing Main Program properties including language."""
    
    def __init__(self, program_name: str, current_language: str, parent=None):
        super().__init__(parent)
        self.program_name = program_name
        self.selected_language = current_language

        self.setWindowTitle(f"Properties - {program_name}")
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout()

        # Program name (read-only)
        layout.addWidget(QLabel("Program Name:"))
        self.name_label = QLabel(program_name)
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label)

        layout.addSpacing(20)

        # Language selection
        layout.addWidget(QLabel("Programming Language:"))
        
        self.lad_radio = QRadioButton("LAD - Ladder Diagram")
        self.lad_radio.toggled.connect(self._on_language_changed)
        layout.addWidget(self.lad_radio)
        
        self.stl_radio = QRadioButton("STL - Statement List")
        self.stl_radio.toggled.connect(self._on_language_changed)
        layout.addWidget(self.stl_radio)

        # Set current selection
        if current_language == "LAD":
            self.lad_radio.setChecked(True)
        else:
            self.stl_radio.setChecked(True)

        layout.addSpacing(20)

        # Description
        self.description_label = QLabel(
            "Changing the language will switch the editor type\n"
            "and update the project tree display."
        )
        self.description_label.setStyleSheet("color: orange;")
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("Apply")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
    
    def _on_language_changed(self) -> None:
        """Handle language radio button change."""
        if self.lad_radio.isChecked():
            self.selected_language = "LAD"
        else:
            self.selected_language = "STL"
    
    def get_selected_language(self) -> str:
        """Return the selected language."""
        return self.selected_language


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
        self.main_program_language = "LAD"  # Default to LAD for main program

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

        scroll = QScrollArea()
        scroll.setWidget(self.grid_container)
        scroll.setWidgetResizable(True)

        layout = QVBoxLayout()
        layout.addLayout(controls)
        layout.addWidget(scroll)
        self.setLayout(layout)

        # Apply default custom profile
        self.apply_custom_profile(30)
    
    def log(self, message, level="INFO"):
        """
        Forward log messages to the parent MainWindow if available.
        Falls back to console output if no parent logger exists.
        """
        if hasattr(self, "main_window") and self.main_window:
            if hasattr(self.main_window, "log"):
                self.main_window.log(message, level)
                return

        # Fallback for standalone usage
        print(f"[{level}] {message}")

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
            self.update_ladder_available_tags()

    def rebuild_from_saved_data(self, pins_data: list, controller_type: str) -> None:
        """Rebuild the pin configuration UI entirely from saved project data."""
        # Clear existing rows
        self.clear_grid()
        
        # Get controller-specific type options from profile if available
        type_options = None
        if self.profile_manager and controller_type.lower() != "custom":
            profile = self.profile_manager.get_profile(controller_type)
            if profile and "type_mapping" in profile:
                # Use controller-specific type options
                type_mapping = profile["type_mapping"]
                type_options = list(type_mapping.values())
        
        # Fall back to generic PIN_TYPES if no controller-specific options
        if not type_options:
            type_options = self.PIN_TYPES
        
        # Create headers
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
        
        # Create a map of saved pins for quick lookup
        saved_pins = {pin["pin"]: pin for pin in pins_data}
        
        # Determine the maximum pin number from saved data
        max_pin = 0
        if saved_pins:
            max_pin = max(saved_pins.keys())
        
        # Build rows from saved data
        for pin_number in range(max_pin + 1):
            pin_label = QLabel(f"GPIO {pin_number}")
            tag_input = QLineEdit()
            pin_type_combo = QComboBox()
            pull_combo = QComboBox()
            pull_combo.addItems(["None", "Pull-Up", "Pull-Down"])
            
            # Get saved data for this pin
            if pin_number in saved_pins:
                saved_data = saved_pins[pin_number]
                tag_name = saved_data.get("tag", "")
                pin_type = saved_data.get("type", "input")
                pull_state = saved_data.get("pull", "none")
            else:
                # Pin not in saved data - use defaults
                tag_name = ""
                pin_type = "input"
                pull_state = "none"
            
            # Set tag
            tag_input.setText(tag_name)
            
            # Set type combo with controller-specific options
            pin_type_combo.addItems(type_options)
            type_index = pin_type_combo.findText(pin_type.capitalize())
            if type_index >= 0:
                pin_type_combo.setCurrentIndex(type_index)
            else:
                # If type not found, try case-insensitive match
                for i in range(pin_type_combo.count()):
                    if pin_type_combo.itemText(i).lower() == pin_type.lower():
                        pin_type_combo.setCurrentIndex(i)
                        break
                else:
                    # If still not found, default to first option
                    pin_type_combo.setCurrentIndex(0)
            
            # Set pull combo
            if pull_state == "up":
                pull_combo.setCurrentText("Pull-Up")
            elif pull_state == "down":
                pull_combo.setCurrentText("Pull-Down")
            else:
                pull_combo.setCurrentText("None")
            
            # Add to grid
            self.grid.addWidget(pin_label, pin_number + 1, 0)
            self.grid.addWidget(tag_input, pin_number + 1, 1)
            self.grid.addWidget(pin_type_combo, pin_number + 1, 2)
            self.grid.addWidget(pull_combo, pin_number + 1, 3)
            
            # Store row reference
            self.rows.append({
                "pin": pin_number,
                "pin_label": pin_label,
                "tag_input": tag_input,
                "type_combo": pin_type_combo,
                "pull_combo": pull_combo,
            })
        
        self.mapping_changed.emit()

    def on_controller_changed(self, controller: str) -> None:
        """Handle controller change."""
        self.log(f"Controller changed to {controller}", "INFO")
        
        # Update label text
        self.controller_label.setText(controller)
        
        # Update navigation tree item
        old_controller_type = self.controller_type
        self.controller_type = controller.lower()
        
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
    def __init__(self, st_code: str, c_code: str, parent=None, ladder_code: str = None, program_language: str = "LAD") -> None:
        super().__init__(parent)
        self.ladder_code = ladder_code
        self.st_code = st_code
        self.c_code = c_code
        self.program_language = program_language
        self.setWindowTitle("Code Preview")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        self.show_lad_button = QPushButton("Show LAD")
        self.show_lad_button.setCheckable(True)
        self.show_lad_button.clicked.connect(self.show_lad)
        top_layout.addWidget(self.show_lad_button)

        self.show_st_button = QPushButton("Show ST")
        self.show_st_button.setCheckable(True)
        self.show_st_button.clicked.connect(self.show_st)
        top_layout.addWidget(self.show_st_button)

        self.show_c_button = QPushButton("Show C")
        self.show_c_button.setCheckable(True)
        self.show_c_button.clicked.connect(self.show_c)
        top_layout.addWidget(self.show_c_button)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        self.code_viewer = QTextEdit()
        self.code_viewer.setReadOnly(True)
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

        # Set default view based on program language
        if self.program_language == "LAD":
            self.show_lad()
        else:
            self.show_st()

    def show_lad(self) -> None:
        self.show_lad_button.setChecked(True)
        self.show_st_button.setChecked(False)
        self.show_c_button.setChecked(False)
        if self.ladder_code:
            self.code_viewer.setPlainText(self.ladder_code)
        else:
            self.code_viewer.setPlainText("Ladder representation is not available.")

    def show_st(self) -> None:
        self.show_lad_button.setChecked(False)
        self.show_st_button.setChecked(True)
        self.show_c_button.setChecked(False)
        self.code_viewer.setPlainText(self.st_code)

    def show_c(self) -> None:
        self.show_lad_button.setChecked(False)
        self.show_st_button.setChecked(False)
        self.show_c_button.setChecked(True)
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
        self.global_variables = []  # Store global variables

        import os
        profiles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "profiles"))
        self.profile_manager = ProfileManager(profiles_dir)

        self.create_menu_bar()

        self.update_program_creation_options()

        self.navigation_tree = QTreeWidget()
        self.navigation_tree.setHeaderHidden(True)
        self.navigation_tree.currentItemChanged.connect(self.change_page)
        self.navigation_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.setup_navigation_tree()

        self.pages = QStackedWidget()
        self.io_mapping_page = self.create_io_mapping_page()
        self.ladder_editor_page = self.create_ladder_editor_page()
        self.st_editor_page = self.create_st_editor_page()
        self.global_variables_page = self.create_global_variables_page()
        self.placeholder_page = self.create_placeholder_page()
        self.pages.addWidget(self.io_mapping_page)
        self.pages.addWidget(self.ladder_editor_page)
        self.pages.addWidget(self.st_editor_page)
        self.pages.addWidget(self.global_variables_page)
        self.pages.addWidget(self.placeholder_page)

        splitter = QSplitter()
        splitter.addWidget(self.navigation_tree)
        splitter.addWidget(self.pages)
        
        # Set fixed minimum width for tree pane
        self.navigation_tree.setMinimumWidth(220)
        
        # Set splitter stretch factors
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        # Set initial splitter sizes
        splitter.setSizes([220, 1000])

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

    def update_ladder_available_tags(self):
        """Update ladder editor available tags from global variables"""
        if not hasattr(self, "ladder_editor"):
            return

        # Build (tag_name, type_name) tuples from global variables
        tags = []
        for var in self.global_variables:
            tag_name = var["name"]
            var_type = var["type"]
            tags.append((tag_name, var_type))

        self.ladder_editor.set_available_tags(tags)

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
            properties_action = QAction("Properties", self)
            properties_action.triggered.connect(self.show_main_program_properties)
            menu.addAction(properties_action)
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(self.delete_main_program)
            menu.addAction(delete_action)
            menu.exec(self.navigation_tree.mapToGlobal(position))

    def create_main_program(self) -> None:
        if self.has_main_program:
            return
        
        # Show New Program dialog
        dialog = NewProgramDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        program_name = dialog.get_program_name()
        language = dialog.get_selected_language()
        
        # Store language in IO mapping widget
        self.io_mapping_widget.main_program_language = language
        
        # Create tree item with language display
        display_name = f"{program_name} [{language}]"
        self.main_program_item = QTreeWidgetItem([display_name])
        self.main_program_item.setData(0, Qt.ItemDataRole.UserRole, {
            "name": program_name,
            "language": language
        })
        self.program_item.addChild(self.main_program_item)
        self.program_item.setExpanded(True)
        self.has_main_program = True
        
        self.update_program_creation_options()
        self.navigation_tree.setCurrentItem(self.main_program_item)
        self._update_editor_placeholder()
        self.log(f"Main Program created (Language: {language})", "INFO")

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
                return
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
            self.program_item.removeChild(self.main_program_item)
            self.main_program_item = None
            self.has_main_program = False
            self.update_program_creation_options()
            self.input_editor.clear()
            self.log("Main Program deleted", "INFO")
    
    def show_main_program_properties(self) -> None:
        """Show properties dialog for Main Program."""
        if not self.has_main_program or not self.main_program_item:
            return
        
        program_info = self.main_program_item.data(0, Qt.ItemDataRole.UserRole)
        if not program_info:
            return
        
        program_name = program_info.get("name", "Main Program")
        current_language = program_info.get("language", "LAD")
        
        # Preserve current program content
        current_content = self.input_editor.toPlainText()
        
        dialog = ProgramPropertiesDialog(program_name, current_language, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_language = dialog.get_selected_language()
            
            if new_language != current_language:
                # Update the language
                self.io_mapping_widget.main_program_language = new_language
                program_info["language"] = new_language
                self.main_program_item.setData(0, Qt.ItemDataRole.UserRole, program_info)
                
                # Update tree display
                display_name = f"{program_name} [{new_language}]"
                self.main_program_item.setText(0, display_name)
                
                # Recreate editor page based on new language
                if new_language == "LAD":
                    # Recreate ladder editor page
                    self.pages.removeWidget(self.ladder_editor_page)
                    self.ladder_editor_page = self.create_ladder_editor_page()
                    self.pages.insertWidget(1, self.ladder_editor_page)
                    
                    # If switching from STL, try to convert text to ladder
                    if current_language == "STL":
                        self.ladder_editor.from_ladder_text(current_content)
                else:
                    # Recreate ST editor page
                    self.pages.removeWidget(self.st_editor_page)
                    self.st_editor_page = self.create_st_editor_page()
                    self.pages.insertWidget(2, self.st_editor_page)
                    
                    # If switching from LAD, convert ladder to text
                    if current_language == "LAD" and hasattr(self, 'ladder_editor'):
                        current_content = self.ladder_editor.to_ladder_text()
                    self.input_editor.setPlainText(current_content)
                
                # Update editor placeholder
                self._update_editor_placeholder()
                
                # Switch to appropriate editor
                self.change_page(self.main_program_item)
                
                self.log(f"Main Program language changed to {new_language}", "INFO")
                self.is_modified = True
                self.update_window_title()

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
        
        # Variables section
        self.variables_item = QTreeWidgetItem(["Variables"])
        self.global_variables_item = QTreeWidgetItem(["Global Variables"])
        self.variables_item.addChild(self.global_variables_item)

        self.navigation_tree.addTopLevelItem(self.controller_item)
        self.navigation_tree.addTopLevelItem(self.program_item)
        self.navigation_tree.addTopLevelItem(self.variables_item)
        self.program_item.setExpanded(True)
        self.variables_item.setExpanded(True)
        
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
        from app.ui.ladder_editor import LadderEditorWidget
        
        # Create graphical ladder editor
        self.ladder_editor = LadderEditorWidget()
        self.ladder_editor.data_changed.connect(self.on_ladder_data_changed)
        
        # Keep text editor for compatibility and as fallback
        self.input_editor = QTextEdit()
        self._update_editor_placeholder()
        self.input_editor.textChanged.connect(self.on_content_changed)
        self.input_editor.hide()  # Hide by default, use graphical editor

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)

        # Create splitter for editor area
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.ladder_editor)
        splitter.addWidget(self.log_viewer)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        # Stretch factors alone only govern extra space on resize - without
        # explicit initial sizes the log panel gets squeezed to ~0 height.
        splitter.setSizes([450, 150])

        layout = QVBoxLayout()
        layout.addWidget(splitter)

        page = QWidget()
        page.setLayout(layout)
        return page

    def create_st_editor_page(self) -> QWidget:
        """Create Structured Text editor page for STL programs"""
        # Use text editor for Structured Text
        self.input_editor = QTextEdit()
        self._update_editor_placeholder()
        self.input_editor.textChanged.connect(self.on_content_changed)
        self.input_editor.show()  # Show text editor for STL

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.input_editor)
        splitter.addWidget(self.log_viewer)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([450, 150])

        layout = QVBoxLayout()
        layout.addWidget(splitter)

        page = QWidget()
        page.setLayout(layout)
        return page
    
    def on_ladder_data_changed(self):
        """
        Synchronize the graphical ladder editor with:
        1. Program.code
        2. Hidden editor widget
        3. Visible lower feedback/code panel
        """
        if not hasattr(self, "ladder_editor"):
            return

        # Generate ladder text
        ladder_text = self.ladder_editor.to_ladder_text()

        # Update the main editor widget
        if hasattr(self, "input_editor") and self.input_editor:
            self.input_editor.blockSignals(True)
            self.input_editor.setPlainText(ladder_text)
            self.input_editor.blockSignals(False)

        # Update the visible lower panel (log_viewer)
        if hasattr(self, "log_viewer") and self.log_viewer:
            self.log_viewer.blockSignals(True)
            self.log_viewer.setPlainText(ladder_text)
            self.log_viewer.blockSignals(False)

        self.on_content_changed()
    
    def _update_editor_placeholder(self) -> None:
        """Update editor placeholder text based on main program language."""
        language = self.io_mapping_widget.main_program_language
        if language == "LAD":
            self.input_editor.setPlaceholderText(
                "Enter ladder logic (e.g., input1 & input2 -> output1)"
            )
        else:
            self.input_editor.setPlaceholderText(
                "Enter structured text (e.g., IF input1 AND input2 THEN output1 := TRUE; END_IF)"
            )

    def create_global_variables_page(self) -> QWidget:
        """Create the global variables editor page"""
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Variable")
        add_btn.clicked.connect(self.add_global_variable)
        toolbar_layout.addWidget(add_btn)
        
        delete_btn = QPushButton("Delete Variable")
        delete_btn.clicked.connect(self.delete_global_variable)
        toolbar_layout.addWidget(delete_btn)
        
        save_btn = QPushButton("Save Variables")
        save_btn.clicked.connect(self.save_global_variables)
        toolbar_layout.addWidget(save_btn)
        
        toolbar_layout.addStretch()
        
        # Table widget
        self.global_variables_table = QTableWidget()
        self.global_variables_table.setColumnCount(5)
        self.global_variables_table.setHorizontalHeaderLabels(["Name", "Type", "Address", "Initial Value", "Comment"])
        self.global_variables_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.global_variables_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.global_variables_table.horizontalHeader().setStretchLastSection(True)
        
        # Set column widths
        self.global_variables_table.setColumnWidth(0, 160)  # Name
        self.global_variables_table.setColumnWidth(1, 200)  # Type
        self.global_variables_table.setColumnWidth(2, 160)  # Address
        self.global_variables_table.setColumnWidth(3, 140)  # Initial Value
        
        # Set up type combo for editing
        self.variable_types = ["BOOL", "INT", "REAL", "STRING", "TON", "TOF", "TP", "COUNTER", "Digital Input", "Digital Output", "Analog Input", "Analog Output"]
        
        layout = QVBoxLayout()
        layout.addLayout(toolbar_layout)
        layout.addWidget(self.global_variables_table)
        
        page = QWidget()
        page.setLayout(layout)
        return page
    
    def add_global_variable(self):
        """Add a new global variable row"""
        row = self.global_variables_table.rowCount()
        self.global_variables_table.insertRow(row)
        
        # Add combo box for type column
        type_combo = QComboBox()
        type_combo.addItems(self.variable_types)
        type_combo.setCurrentText("BOOL")
        self.global_variables_table.setCellWidget(row, 1, type_combo)
        
        # Connect type change to update address column
        type_combo.currentTextChanged.connect(lambda text, r=row: self.on_type_changed(r, text))
        
        # Add address combo for physical I/O, or text item for internal types
        self.update_address_column(row, "BOOL")
        
        # Add default values
        self.global_variables_table.setItem(row, 0, QTableWidgetItem(f"VAR{row + 1}"))
        self.global_variables_table.setItem(row, 3, QTableWidgetItem(""))  # Initial Value
        self.global_variables_table.setItem(row, 4, QTableWidgetItem(""))  # Comment
    
    def delete_global_variable(self):
        """Delete selected global variable row"""
        selected_row = self.global_variables_table.currentRow()
        if selected_row >= 0:
            self.global_variables_table.removeRow(selected_row)
    
    def on_type_changed(self, row: int, new_type: str):
        """Handle type combo change to update address column"""
        self.update_address_column(row, new_type)
    
    def update_address_column(self, row: int, var_type: str):
        """Update address column based on variable type"""
        # Physical I/O types need GPIO dropdown
        physical_io_types = ["Digital Input", "Digital Output", "Analog Input", "Analog Output"]
        
        # Remove existing cell widget or item
        if self.global_variables_table.cellWidget(row, 2):
            self.global_variables_table.removeCellWidget(row, 2)
        if self.global_variables_table.item(row, 2):
            self.global_variables_table.takeItem(row, 2)
        
        if var_type in physical_io_types:
            # Create GPIO dropdown
            address_combo = QComboBox()
            address_combo.setEditable(True)
            
            # Get valid pins with annotations from controller profile, excluding duplicates
            pins_with_annotations = self.get_valid_pins_with_annotations(var_type, row)
            
            # Add pins with annotations to combo box
            for pin_name, annotation in pins_with_annotations:
                if annotation:
                    display_text = f"{pin_name} ({annotation})"
                else:
                    display_text = pin_name
                address_combo.addItem(display_text, pin_name)  # Store actual pin name as data
            
            self.global_variables_table.setCellWidget(row, 2, address_combo)
        else:
            # Use text item for internal types with auto-generated address
            auto_address = self.generate_internal_address(var_type, row)
            address_item = QTableWidgetItem(auto_address)
            address_item.setFlags(address_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Disable editing
            self.global_variables_table.setItem(row, 2, address_item)
    
    def generate_internal_address(self, var_type: str, current_row: int) -> str:
        """Generate auto-generated internal address based on variable type"""
        # Get used internal addresses to avoid duplicates
        used_internal_addresses = self.get_used_internal_addresses(current_row)
        
        if var_type == "BOOL":
            # Generate M1, M2, M3...
            prefix = "M"
            return self.find_next_available_address(prefix, used_internal_addresses)
        elif var_type == "INT":
            # Generate MW1, MW2, MW3...
            prefix = "MW"
            return self.find_next_available_address(prefix, used_internal_addresses)
        elif var_type == "REAL":
            # Generate MD1, MD2, MD3...
            prefix = "MD"
            return self.find_next_available_address(prefix, used_internal_addresses)
        elif var_type == "STRING":
            # Generate STR1, STR2, STR3...
            prefix = "STR"
            return self.find_next_available_address(prefix, used_internal_addresses)
        elif var_type in ["TON", "TOF", "TP"]:
            # Generate T1, T2, T3...
            prefix = "T"
            return self.find_next_available_address(prefix, used_internal_addresses)
        elif var_type == "COUNTER":
            # Generate C1, C2, C3...
            prefix = "C"
            return self.find_next_available_address(prefix, used_internal_addresses)
        else:
            # Fallback to empty string
            return ""
    
    def find_next_available_address(self, prefix: str, used_addresses: set) -> str:
        """Find the next available address with the given prefix"""
        counter = 1
        while True:
            address = f"{prefix}{counter}"
            if address not in used_addresses:
                return address
            counter += 1
    
    def get_used_internal_addresses(self, current_row: int) -> set:
        """Get set of internal addresses already used by other rows"""
        used_addresses = set()
        internal_types = ["BOOL", "INT", "REAL", "STRING", "TON", "TOF", "TP", "COUNTER"]
        
        for row in range(self.global_variables_table.rowCount()):
            if row == current_row:
                continue  # Skip the current row being edited
            
            type_widget = self.global_variables_table.cellWidget(row, 1)
            if not type_widget:
                continue
            
            var_type = type_widget.currentText()
            if var_type not in internal_types:
                continue
            
            # Get address
            address_item = self.global_variables_table.item(row, 2)
            address = address_item.text() if address_item else ""
            
            if address:
                used_addresses.add(address)
        
        return used_addresses
    
    def get_valid_pins_with_annotations(self, var_type: str, current_row: int = -1) -> list:
        """Get valid GPIO pins with annotations for the given variable type"""
        controller_type = self.io_mapping_widget.controller_type.lower()
        
        # Get used GPIO addresses to exclude duplicates
        used_addresses = self.get_used_gpio_addresses(current_row)
        
        # Default pins for Custom controller (no restrictions)
        if controller_type == "custom":
            pins = [(f"GPIO{i}", "") for i in range(40)]
            return [p for p in pins if p[0] not in used_addresses]
        
        # Get controller profile
        if self.profile_manager:
            profile = self.profile_manager.get_profile(controller_type)
            if profile:
                pin_config = profile.get("pin_config", {})
                
                # If pin_config exists and has the required fields, use it
                if pin_config and any("input_only" in pin_config.get(k, {}) for k in pin_config.keys()):
                    valid_pins = []
                    for pin_name, pin_info in pin_config.items():
                        is_input_only = pin_info.get("input_only", False)
                        is_adc = pin_info.get("adc", False)
                        is_dac = pin_info.get("dac", False)
                        is_reserved = pin_info.get("reserved", False)
                        is_boot_pin = pin_info.get("boot_pin", False)
                        
                        # Skip reserved pins
                        if is_reserved:
                            continue
                        
                        # Skip already-used addresses
                        if pin_name in used_addresses:
                            continue
                        
                        # Filter by type
                        if var_type == "Digital Input":
                            valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                        elif var_type == "Digital Output":
                            if not is_input_only:
                                valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                        elif var_type == "Analog Input":
                            if is_adc:
                                valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                        elif var_type == "Analog Output":
                            if is_dac:
                                valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                    
                    valid_pins.sort(key=lambda x: int(x[0].replace("GPIO", "")) if x[0].startswith("GPIO") else 0)
                    return valid_pins
        
        # Fallback: Use hardcoded restrictions for known controllers
        return self.get_hardcoded_pins_for_controller(controller_type, var_type, used_addresses)
    
    def get_hardcoded_pins_for_controller(self, controller_type: str, var_type: str, used_addresses: set) -> list:
        """Get valid pins using hardcoded restrictions for known controllers"""
        controller_type = controller_type.lower()
        pins = []
        
        if controller_type == "esp32":
            # ESP32 pin restrictions - exact specification
            # Boot strapping pins (DO NOT SHOW): GPIO0, GPIO2, GPIO12, GPIO15
            boot_pins = {"GPIO0", "GPIO2", "GPIO12", "GPIO15"}
            # UART programming pins (DO NOT SHOW): GPIO1, GPIO3
            uart_pins = {"GPIO1", "GPIO3"}
            # Flash memory pins (DO NOT SHOW): GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO11
            flash_pins = {"GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11"}
            # Safe general purpose GPIOs
            safe_general = {"GPIO4", "GPIO5", "GPIO13", "GPIO14", "GPIO16", "GPIO17", "GPIO18", "GPIO19", 
                          "GPIO21", "GPIO22", "GPIO23", "GPIO25", "GPIO26", "GPIO27", "GPIO32", "GPIO33"}
            # Safe input-only GPIOs
            input_only = {"GPIO34", "GPIO35", "GPIO36", "GPIO39"}
            
            # Combined excluded pins
            excluded_pins = boot_pins | uart_pins | flash_pins
            
            for i in range(40):
                pin_name = f"GPIO{i}"
                
                # Skip excluded pins
                if pin_name in excluded_pins:
                    continue
                
                # Skip already-used addresses
                if pin_name in used_addresses:
                    continue
                
                annotations = []
                
                if var_type == "Digital Input":
                    # Allow safe general purpose + input-only pins
                    if pin_name in safe_general or pin_name in input_only:
                        if pin_name in input_only:
                            annotations.append("Input Only")
                        pins.append((pin_name, " | ".join(annotations) if annotations else ""))
                    
                elif var_type == "Digital Output":
                    # Allow only safe general purpose pins (exclude input-only)
                    if pin_name in safe_general:
                        pins.append((pin_name, " | ".join(annotations) if annotations else ""))
                        
                elif var_type == "Analog Input":
                    # Only ADC-capable pins (safe general purpose + input-only that are ADC-capable)
                    adc_pins = safe_general | {"GPIO34", "GPIO35", "GPIO36", "GPIO39"}
                    if pin_name in adc_pins:
                        if pin_name in input_only:
                            annotations.append("Input Only")
                        annotations.append("ADC")
                        pins.append((pin_name, " | ".join(annotations) if annotations else ""))
                        
                elif var_type == "Analog Output":
                    # Only DAC-capable pins (GPIO25, GPIO26)
                    dac_pins = {"GPIO25", "GPIO26"}
                    if pin_name in dac_pins:
                        annotations.append("DAC")
                        pins.append((pin_name, " | ".join(annotations) if annotations else ""))
                        
        elif controller_type == "esp8266":
            # ESP8266 has GPIO 0-15, but GPIO6-11 are used for flash
            # Boot pin: GPIO0
            # UART pins: GPIO1, GPIO3
            # Flash pins: GPIO6, GPIO7, GPIO8, GPIO9, GPIO10, GPIO11
            excluded_pins = {"GPIO0", "GPIO1", "GPIO3", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11"}
            safe_general = {"GPIO2", "GPIO4", "GPIO5", "GPIO12", "GPIO13", "GPIO14", "GPIO15"}
            
            for i in range(16):
                pin_name = f"GPIO{i}"
                
                if pin_name in excluded_pins:
                    continue
                
                if pin_name in used_addresses:
                    continue
                
                if var_type in ["Digital Input", "Digital Output"]:
                    if pin_name in safe_general:
                        pins.append((pin_name, ""))
                    
        else:
            # Generic fallback - allow all GPIO0-39 except those in used_addresses
            for i in range(40):
                pin_name = f"GPIO{i}"
                if pin_name not in used_addresses:
                    pins.append((pin_name, ""))
        
        return pins
    
    def get_used_gpio_addresses(self, current_row: int) -> set:
        """Get set of GPIO addresses already used by other rows"""
        used_addresses = set()
        physical_io_types = ["Digital Input", "Digital Output", "Analog Input", "Analog Output"]
        
        for row in range(self.global_variables_table.rowCount()):
            if row == current_row:
                continue  # Skip the current row being edited
            
            type_widget = self.global_variables_table.cellWidget(row, 1)
            if not type_widget:
                continue
            
            var_type = type_widget.currentText()
            if var_type not in physical_io_types:
                continue
            
            # Get address
            address_widget = self.global_variables_table.cellWidget(row, 2)
            if isinstance(address_widget, QComboBox):
                address = address_widget.currentData()
                if address is None:
                    address = address_widget.currentText()
            else:
                address_item = self.global_variables_table.item(row, 2)
                address = address_item.text() if address_item else ""
            
            if address:
                used_addresses.add(address)
        
        return used_addresses
    
    def get_valid_pins_for_type(self, var_type: str) -> list:
        """Get valid GPIO pins for the given variable type based on controller profile"""
        controller_type = self.io_mapping_widget.controller_type.lower()
        
        # Default pins for Custom controller
        if controller_type == "custom":
            return [f"GPIO{i}" for i in range(40)]
        
        # Get controller profile
        if self.profile_manager:
            profile = self.profile_manager.get_profile(controller_type)
            if profile:
                pin_config = profile.get("pin_config", {})
                
                # Filter pins based on type
                valid_pins = []
                for pin_name, pin_info in pin_config.items():
                    is_input_only = pin_info.get("input_only", False)
                    is_adc = pin_info.get("adc", False)
                    is_dac = pin_info.get("dac", False)
                    is_reserved = pin_info.get("reserved", False)
                    is_boot_pin = pin_info.get("boot_pin", False)
                    
                    # Skip reserved pins
                    if is_reserved:
                        continue
                    
                    # Filter by type
                    if var_type == "Digital Input":
                        # Allow input pins and input-only pins
                        valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                    elif var_type == "Digital Output":
                        # Block input-only pins
                        if not is_input_only:
                            valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                    elif var_type == "Analog Input":
                        # Only ADC-capable pins
                        if is_adc:
                            valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                    elif var_type == "Analog Output":
                        # Only DAC-capable pins
                        if is_dac:
                            valid_pins.append((pin_name, self.get_pin_annotation(pin_info)))
                
                # Sort by GPIO number
                valid_pins.sort(key=lambda x: int(x[0].replace("GPIO", "")) if x[0].startswith("GPIO") else 0)
                return [pin[0] for pin in valid_pins]  # Return only pin names for combo box
        
        # Fallback to default pins
        return [f"GPIO{i}" for i in range(40)]
    
    def get_pin_annotation(self, pin_info: dict) -> str:
        """Get annotation text for pin status"""
        annotations = []
        
        if pin_info.get("input_only", False):
            annotations.append("Input Only")
        if pin_info.get("boot_pin", False):
            annotations.append("Boot Pin")
        if pin_info.get("adc", False):
            annotations.append("ADC")
        if pin_info.get("dac", False):
            annotations.append("DAC")
        
        return " | ".join(annotations) if annotations else ""
    
    def validate_global_variables(self) -> list:
        """Validate global variables and return list of error messages"""
        errors = []
        
        # Track used GPIO addresses for physical I/O
        gpio_addresses = {}
        physical_io_types = ["Digital Input", "Digital Output", "Analog Input", "Analog Output"]
        
        for row in range(self.global_variables_table.rowCount()):
            name_item = self.global_variables_table.item(row, 0)
            type_widget = self.global_variables_table.cellWidget(row, 1)
            
            # Get address from combo box or text item
            address_widget = self.global_variables_table.cellWidget(row, 2)
            if isinstance(address_widget, QComboBox):
                address_value = address_widget.currentText()
            else:
                address_item = self.global_variables_table.item(row, 2)
                address_value = address_item.text() if address_item else ""
            
            if name_item and type_widget:
                var_name = name_item.text()
                var_type = type_widget.currentText()
                
                # Check for missing name
                if not var_name:
                    errors.append(f"Row {row + 1}: Variable name is missing")
                
                # Check for missing type
                if not var_type:
                    errors.append(f"Row {row + 1}: Variable type is missing")
                
                # Check for missing address for physical I/O
                if var_type in physical_io_types and not address_value:
                    errors.append(f"Row {row + 1} ({var_name}): Address is required for {var_type}")
                
                # Check for duplicate GPIO addresses
                if var_type in physical_io_types and address_value:
                    if address_value in gpio_addresses:
                        errors.append(f"Row {row + 1} ({var_name}): GPIO address '{address_value}' is already used by {gpio_addresses[address_value]}")
                    else:
                        gpio_addresses[address_value] = var_name
        
        return errors
    
    def save_global_variables(self):
        """Save global variables to internal storage and update ladder editor"""
        self.global_variables = []
        for row in range(self.global_variables_table.rowCount()):
            name_item = self.global_variables_table.item(row, 0)
            type_widget = self.global_variables_table.cellWidget(row, 1)
            value_item = self.global_variables_table.item(row, 3)
            comment_item = self.global_variables_table.item(row, 4)
            
            # Get address from combo box or text item
            address_widget = self.global_variables_table.cellWidget(row, 2)
            if isinstance(address_widget, QComboBox):
                # Get the actual pin name from data, not the display text
                address_value = address_widget.currentData()
                if address_value is None:
                    # If user typed a custom value, use that
                    address_value = address_widget.currentText()
            else:
                address_item = self.global_variables_table.item(row, 2)
                address_value = address_item.text() if address_item else ""
            
            if name_item and type_widget:
                var_data = {
                    "name": name_item.text(),
                    "type": type_widget.currentText(),
                    "address": address_value,
                    "initial_value": value_item.text() if value_item else "",
                    "comment": comment_item.text() if comment_item else ""
                }
                self.global_variables.append(var_data)
        
        # Validate for duplicate GPIO addresses
        validation_errors = self.validate_global_variables()
        if validation_errors:
            error_msg = "\n".join(validation_errors)
            QMessageBox.warning(self, "Validation Errors", error_msg)
            return
        
        self.log(f"Saved {len(self.global_variables)} global variables", "INFO")
        
        # Update ladder editor available tags
        self.update_ladder_available_tags()
    
    def load_global_variables_to_table(self):
        """Load global variables from internal storage to the table"""
        self.global_variables_table.setRowCount(0)
        for var in self.global_variables:
            row = self.global_variables_table.rowCount()
            self.global_variables_table.insertRow(row)
            
            # Add combo box for type column
            type_combo = QComboBox()
            type_combo.addItems(self.variable_types)
            type_combo.setCurrentText(var["type"])
            self.global_variables_table.setCellWidget(row, 1, type_combo)
            
            # Connect type change to update address column
            type_combo.currentTextChanged.connect(lambda text, r=row: self.on_type_changed(r, text))
            
            # Add values
            self.global_variables_table.setItem(row, 0, QTableWidgetItem(var["name"]))
            
            # Set address based on type
            self.update_address_column(row, var["type"])
            address_value = var.get("address", "")
            
            # If it's a combo box, set the text
            if self.global_variables_table.cellWidget(row, 2):
                address_combo = self.global_variables_table.cellWidget(row, 2)
                if isinstance(address_combo, QComboBox):
                    # Try to find the pin in the combo box by data
                    index = address_combo.findData(address_value)
                    if index >= 0:
                        address_combo.setCurrentIndex(index)
                    else:
                        # If not found, set as custom text
                        address_combo.setCurrentText(address_value)
            else:
                self.global_variables_table.setItem(row, 2, QTableWidgetItem(address_value))
            
            self.global_variables_table.setItem(row, 3, QTableWidgetItem(var.get("initial_value", "")))  # Initial Value
            self.global_variables_table.setItem(row, 4, QTableWidgetItem(var.get("comment", "")))  # Comment

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
    
    def update_controller_display(self, controller_name: str) -> None:
        """Compatibility wrapper for update_controller_tree_item."""
        self.update_controller_tree_item(controller_name)

    def on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click on tree items"""
        if item is self.controller_item:
            # Open controller selection dialog
            dialog = ControllerSelectionDialog(self.profile_manager, self.io_mapping_widget.controller_type, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_controller = dialog.get_selected_controller()
                if selected_controller:
                    self.io_mapping_widget.controller_type = selected_controller
                    self.update_controller_tree_item(selected_controller)
                    self.log(f"Controller changed to {selected_controller}", "INFO")
                    
                    # Revalidate all variable addresses for new controller
                    self.revalidate_addresses_for_controller_change(selected_controller)
    
    def revalidate_addresses_for_controller_change(self, new_controller: str):
        """Revalidate all variable addresses when controller changes"""
        invalid_addresses = []
        physical_io_types = ["Digital Input", "Digital Output", "Analog Input", "Analog Output"]
        
        # Check if Global Variables page is currently visible
        if self.pages.currentWidget() != self.global_variables_page:
            # Not visible, just validate without UI updates
            for var in self.global_variables:
                if var["type"] in physical_io_types:
                    address = var.get("address", "")
                    if address:
                        valid_pins = self.get_valid_pins_for_type(var["type"])
                        if address not in valid_pins:
                            invalid_addresses.append(f"{var['name']} ({var['type']}): {address}")
            
            if invalid_addresses:
                warning_msg = "The following GPIO addresses are invalid for the new controller:\n\n" + "\n".join(invalid_addresses)
                warning_msg += "\n\nPlease review and update the Global Variables."
                QMessageBox.warning(self, "Controller Change Warning", warning_msg)
        else:
            # Global Variables page is visible, update the dropdowns
            for row in range(self.global_variables_table.rowCount()):
                type_widget = self.global_variables_table.cellWidget(row, 1)
                if type_widget:
                    var_type = type_widget.currentText()
                    if var_type in physical_io_types:
                        # Refresh the address dropdown with new valid pins
                        self.update_address_column(row, var_type)
                        
                        # Try to preserve the current address if it's still valid
                        address_widget = self.global_variables_table.cellWidget(row, 2)
                        if isinstance(address_widget, QComboBox):
                            # Get current address from the saved variable data
                            if row < len(self.global_variables):
                                current_address = self.global_variables[row].get("address", "")
                                if current_address:
                                    index = address_widget.findData(current_address)
                                    if index >= 0:
                                        address_widget.setCurrentIndex(index)
                                    else:
                                        # Address is no longer valid, highlight it
                                        invalid_addresses.append(f"{self.global_variables[row]['name']} ({var_type}): {current_address}")
            
            if invalid_addresses:
                warning_msg = "The following GPIO addresses are invalid for the new controller:\n\n" + "\n".join(invalid_addresses)
                warning_msg += "\n\nPlease update these addresses in the Global Variables table."
                QMessageBox.warning(self, "Controller Change Warning", warning_msg)

    def change_page(self, current: QTreeWidgetItem, previous: QTreeWidgetItem = None) -> None:
        if current is self.controller_item:
            # Controller node now only shows placeholder - configuration is done via Global Variables
            self.pages.setCurrentWidget(self.placeholder_page)
        elif current is self.program_item:
            if self.has_main_program:
                # Show appropriate editor based on program language
                language = self.io_mapping_widget.main_program_language
                if language == "LAD":
                    self.pages.setCurrentWidget(self.ladder_editor_page)
                    # Load ladder content from input editor
                    if hasattr(self, 'ladder_editor') and hasattr(self, 'input_editor'):
                        current_content = self.input_editor.toPlainText()
                        self.ladder_editor.from_ladder_text(current_content)
                    self.update_ladder_available_tags()
                else:
                    self.pages.setCurrentWidget(self.st_editor_page)
            else:
                self.pages.setCurrentWidget(self.placeholder_page)
        elif current is self.main_program_item:
            # Show appropriate editor based on program language
            language = self.io_mapping_widget.main_program_language
            if language == "LAD":
                self.pages.setCurrentWidget(self.ladder_editor_page)
                # Load ladder content from input editor
                if hasattr(self, 'ladder_editor') and hasattr(self, 'input_editor'):
                    current_content = self.input_editor.toPlainText()
                    self.ladder_editor.from_ladder_text(current_content)
                self.update_ladder_available_tags()
            else:
                self.pages.setCurrentWidget(self.st_editor_page)
        elif current is self.global_variables_item:
            self.pages.setCurrentWidget(self.global_variables_page)
            self.load_global_variables_to_table()

    def compile_ladder(self) -> None:
        try:
            self.log("Compilation started", "INFO")
            source_code = self.input_editor.toPlainText()
            project_language = self.io_mapping_widget.main_program_language
            
            # Validate based on language
            if project_language == "LAD":
                errors = validation(self.get_validation_mapping(), source_code, self.global_variables)
                if errors:
                    self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                    dialog = ValidationErrorsDialog(errors, self)
                    dialog.exec()
                    return
                # Convert ladder to ST
                st_code = ladder_to_st(source_code)
            else:
                # STL - use directly
                errors = validation(self.get_validation_mapping(), source_code, self.global_variables)
                if errors:
                    self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                    dialog = ValidationErrorsDialog(errors, self)
                    dialog.exec()
                    return
                st_code = source_code
            
            controller_config_dict = self.io_mapping_widget.controller_config.to_dict()
            c_code = compile_st_to_c(st_code, self.get_mapping(), controller_config_dict)
            self.compiled_code = c_code
            
            # Display compiled code in the lower panel
            if hasattr(self, "log_viewer") and self.log_viewer:
                self.log_viewer.setPlainText(c_code)
            
            self.log("Compilation completed successfully", "SUCCESS")
        except Exception as error:
            self.log(f"Compilation error: {error}", "ERROR")

    def convert_ladder(self) -> None:
        try:
            self.log("Conversion started", "INFO")
            source_code = self.input_editor.toPlainText()
            project_language = self.io_mapping_widget.main_program_language
            
            # Validate based on language
            if project_language == "LAD":
                errors = validation(self.get_validation_mapping(), source_code, self.global_variables)
                if errors:
                    self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                    dialog = ValidationErrorsDialog(errors, self)
                    dialog.exec()
                    return
                # Convert ladder to ST
                st_code = ladder_to_st(source_code)
                ladder_code = source_code  # Store original ladder code
            else:
                # STL - use directly
                errors = validation(self.get_validation_mapping(), source_code, self.global_variables)
                if errors:
                    self.log(f"Validation failed: {len(errors)} error(s)", "ERROR")
                    dialog = ValidationErrorsDialog(errors, self)
                    dialog.exec()
                    return
                st_code = source_code
                ladder_code = None  # No ladder code for STL projects
            
            controller_config_dict = self.io_mapping_widget.controller_config.to_dict()
            c_code = compile_st_to_c(st_code, self.get_mapping(), controller_config_dict)

            dialog = CodePreviewDialog(st_code, c_code, self, ladder_code, project_language)
            dialog.exec()
            
            # Display converted code in the lower panel
            if hasattr(self, "log_viewer") and self.log_viewer:
                self.log_viewer.setPlainText(st_code)
            
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
        
        # Create project immediately without popup
        self.io_mapping_widget.project_language = "LAD"  # Default to LAD
        self.log("New project created", "INFO")
        self.input_editor.clear()
        self._update_editor_placeholder()
        self.compiled_code = None
        self.io_mapping_widget.on_controller_changed("Custom")
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
            
            pins_data = []
            for row in self.io_mapping_widget.rows:
                pin_type = row["type_combo"].currentText()
                tag_name = row["tag_input"].text().strip()
                pull_text = row["pull_combo"].currentText()
                pull_state = "none"
                if pull_text == "Pull-Up":
                    pull_state = "up"
                elif pull_text == "Pull-Down":
                    pull_state = "down"
                
                pins_data.append({
                    "pin": row["pin"],
                    "tag": tag_name,
                    "type": pin_type.lower(),
                    "pull": pull_state,
                })
            
            project_data = {
                "controller": self.io_mapping_widget.controller_type,
                "pin_count": self.io_mapping_widget.pin_count.value(),
                "has_main_program": self.has_main_program,
                "pins": pins_data,
                "program": program_text,
                "global_variables": self.global_variables,
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
            
            if "pins" not in project_data or "program" not in project_data:
                raise ValueError("Missing required fields in project file")
            
            self.input_editor.setPlainText(project_data["program"])
            self._update_editor_placeholder()
            self.compiled_code = None
            
            # Load global variables if exists
            global_variables_data = project_data.get("global_variables")
            if global_variables_data:
                self.global_variables = global_variables_data
            else:
                self.global_variables = []
            
            # Load main program data if exists
            main_program_data = project_data.get("main_program")
            if main_program_data:
                program_name = main_program_data.get("name", "Main Program")
                language = main_program_data.get("language", "LAD")
                self.io_mapping_widget.main_program_language = language
                
                has_main_program = project_data.get("has_main_program", False)
                if has_main_program and not self.has_main_program:
                    display_name = f"{program_name} [{language}]"
                    self.main_program_item = QTreeWidgetItem([display_name])
                    self.main_program_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "name": program_name,
                        "language": language
                    })
                    self.program_item.addChild(self.main_program_item)
                    self.program_item.setExpanded(True)
                    self.has_main_program = True
                    self.update_program_creation_options()
            else:
                # Backward compatibility for old projects
                self.io_mapping_widget.main_program_language = "LAD"
                has_main_program = project_data.get("has_main_program", False)
                if has_main_program and not self.has_main_program:
                    self.main_program_item = QTreeWidgetItem(["Main Program"])
                    self.main_program_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "name": "Main Program",
                        "language": "LAD"
                    })
                    self.program_item.addChild(self.main_program_item)
                    self.program_item.setExpanded(True)
                    self.has_main_program = True
                    self.update_program_creation_options()
            
            controller_type = project_data.get("controller", "custom")
            
            # Apply controller profile first to get correct type options
            # This will rebuild the UI with profile defaults, which we'll immediately override
            self.io_mapping_widget.on_controller_changed(controller_type.capitalize())
            
            # Set pin count
            pin_count = project_data.get("pin_count", 30)
            self.io_mapping_widget.pin_count.setValue(pin_count)
            
            # Rebuild UI entirely from saved project data (with correct controller options)
            # This overrides the profile defaults with the actual saved configuration
            self.io_mapping_widget.rebuild_from_saved_data(project_data["pins"], controller_type)
            
            self.current_file_path = file_path
            self.update_ladder_available_tags()
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
