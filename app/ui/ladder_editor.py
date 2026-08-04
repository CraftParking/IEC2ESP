"""
Graphical Ladder Editor for IEC2ESP
Inspired by LDmicro - drag-and-drop ladder diagram editor
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QPushButton, QLabel, QFrame, QDialog, QLineEdit, QMenu, QStyle,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox
)
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QDrag, QPainter
from typing import List, Dict, Optional, Any

# Comfortable cell sizing bounds - cells shrink to fit narrow windows but
# never stretch past a size where the ladder symbols look sparse/lost.
MIN_CELL_WIDTH = 90
MAX_CELL_WIDTH = 130
CELL_HEIGHT = 46
RUNG_GAP = 8
# Left-hand gutter reserved for the rung number, kept in positive scene
# coordinates so it isn't clipped by the top-left-anchored view.
NUMBER_GUTTER = 26


class LadderCellItem(QGraphicsRectItem):
    """A single cell in the ladder grid - displays wire or ladder symbol"""
    
    def __init__(self, row: int, col: int, cell_size: QSize = QSize(120, 60)):
        super().__init__(0, 0, cell_size.width(), cell_size.height())
        self.row = row
        self.col = col
        self.cell_size = cell_size
        self.element_type: Optional[str] = None  # None, "contact_no", "contact_nc", "coil", "timer_ton"
        self.tag: str = ""
        self.pt: int = 1000  # Preset time in milliseconds (default for timers)
        self.setAcceptDrops(True)
        self.setAcceptHoverEvents(True)

        # No permanent border - real ladder software draws a plain wire, not
        # a spreadsheet grid. A border only appears as hover/drag feedback.
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(1)  # Above rung
        
        # Enable selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    
    def set_element(self, element_type: str, tag: str = "", pt: int = 1000):
        """Set the element type, tag, and preset time for this cell"""
        self.element_type = element_type
        self.tag = tag
        self.pt = pt
        self.update()
    
    def clear_element(self):
        """Clear the element and restore default wire"""
        self.element_type = None
        self.tag = ""
        self.update()
    
    def _paint_symbol(self, painter, option, widget):
        """Paint a plain wire segment or ladder symbol - no cell grid box,
        matching how real ladder software (e.g. WPLSoft) renders a rung."""
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        tag_height = 13

        # Symbol sits on the wire, vertically centered below the tag label
        y = rect.top() + tag_height + (h - tag_height) / 2

        if self.element_type is None:
            # Default: plain horizontal wire across the full cell width
            painter.setPen(QPen(QColor("black"), 2))
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        else:
            # Draw tag name above the symbol
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.setPen(QPen(QColor("black")))
            painter.drawText(
                QRectF(rect.left(), rect.top(), rect.width(), tag_height),
                Qt.AlignmentFlag.AlignCenter,
                self.tag
            )

            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

            # Compute coordinates using percentages
            x1 = rect.left() + w * 0.30
            x2 = rect.left() + w * 0.70
            bar_half = min(9, (h - tag_height) / 2 - 2)

            if self.element_type == "contact_no":
                # NO Contact: ----| |----
                painter.drawLine(int(rect.left()), int(y), int(x1), int(y))
                painter.drawLine(int(x2), int(y), int(rect.right()), int(y))
                painter.drawLine(int(x1), int(y - bar_half), int(x1), int(y + bar_half))
                painter.drawLine(int(x2), int(y - bar_half), int(x2), int(y + bar_half))

            elif self.element_type == "contact_nc":
                # NC Contact: ----|/|----
                painter.drawLine(int(rect.left()), int(y), int(x1), int(y))
                painter.drawLine(int(x2), int(y), int(rect.right()), int(y))
                painter.drawLine(int(x1), int(y - bar_half), int(x1), int(y + bar_half))
                painter.drawLine(int(x2), int(y - bar_half), int(x2), int(y + bar_half))
                painter.drawLine(int(x1 + 2), int(y + bar_half), int(x2 - 2), int(y - bar_half))

            elif self.element_type == "coil":
                # Coil: ----( )----
                x1 = rect.left() + w * 0.35
                x2 = rect.left() + w * 0.65
                coil_width = w * 0.12
                coil_height = min(20, h - tag_height - 4)

                left_arc = QRectF(x1 - coil_width, y - coil_height / 2,
                                  coil_width * 2, coil_height)
                right_arc = QRectF(x2 - coil_width, y - coil_height / 2,
                                   coil_width * 2, coil_height)

                painter.drawLine(int(rect.left()), int(y), int(x1 - coil_width), int(y))
                painter.drawLine(int(x2 + coil_width), int(y), int(rect.right()), int(y))

                painter.drawArc(left_arc, 90 * 16, 180 * 16)
                painter.drawArc(right_arc, -90 * 16, 180 * 16)

            elif self.element_type == "timer_ton":
                # Compact inline instruction block, e.g. "TON  T1  1000ms" -
                # sits on the wire like a coil rather than a tall stacked box.
                block_height = min(22, h - tag_height - 4)
                block_width = w * 0.7
                block_rect = QRectF(
                    rect.left() + (w - block_width) / 2,
                    y - block_height / 2,
                    block_width,
                    block_height,
                )

                painter.drawLine(int(rect.left()), int(y), int(block_rect.left()), int(y))
                painter.drawLine(int(block_rect.right()), int(y), int(rect.right()), int(y))

                painter.setPen(QPen(QColor(0, 0, 150), 1))
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawRect(block_rect)

                painter.setPen(QPen(QColor(0, 0, 0)))
                inline_font = QFont()
                inline_font.setPointSize(7)
                painter.setFont(inline_font)
                painter.drawText(
                    block_rect, Qt.AlignmentFlag.AlignCenter,
                    f"TON {self.tag} {self.pt}ms"
                )

        # Draw selection highlight
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor(0, 100, 255), 1))  # Blue outline
            painter.setBrush(QBrush(QColor(200, 220, 255, 60)))  # Faint blue fill
            painter.drawRect(self.rect())

    def paint(self, painter, option, widget):
        # Hover/drag feedback is the only time this cell shows any box at
        # all - drawn first, underneath the wire/symbol.
        if self.brush().style() != Qt.BrushStyle.NoBrush:
            painter.fillRect(self.rect(), self.brush())
        self._paint_symbol(painter, option, widget)

    def hoverEnterEvent(self, event):
        """Highlight on hover"""
        self.setBrush(QBrush(QColor(230, 230, 250, 120)))  # Light blue with transparency for hover
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Remove highlight"""
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.update()
        super().hoverLeaveEvent(event)
    
    def dragEnterEvent(self, event):
        """Accept drag from toolbox"""
        if event.mimeData().hasFormat("application/x-ladder-element"):
            event.acceptProposedAction()
            self.setBrush(QBrush(QColor(230, 230, 250, 120)))  # Light blue with transparency for drag
            self.update()

    def dragLeaveEvent(self, event):
        """Remove highlight on drag leave"""
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.update()

    def dropEvent(self, event):
        """Handle drop from toolbox"""
        element_type = event.mimeData().data("application/x-ladder-element").data().decode()

        # Set element type directly on cell with default values
        if element_type == "timer_ton":
            self.set_element(element_type, "T1", 1000)  # Default tag and PT
        else:
            self.set_element(element_type, "")

        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.update()
        event.acceptProposedAction()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click to edit tag or configure timer"""
        if not self.element_type:
            return

        scene = self.scene()
        if scene is None:
            return

        # parent_widget is an attribute, not a function
        editor = scene.parent_widget
        if editor is None:
            return

        # Use the graphics view as the dialog parent
        view = scene.views()[0] if scene.views() else None

        # For timers, use TimerConfigDialog
        if self.element_type == "timer_ton":
            dialog = TimerConfigDialog(self.tag, self.pt, view)
            if dialog.exec():
                timer_tag, timer_pt = dialog.get_config()
                self.tag = timer_tag
                self.pt = timer_pt
                self.update()
                editor.data_changed.emit()
        else:
            # For contacts and coils, use TagSelectionDialog
            available_tags = editor.get_available_tags()

            dialog = TagSelectionDialog(available_tags, self.element_type, self.tag, view)
            if dialog.exec():
                selected_tag = dialog.get_selected_tag()
                if selected_tag:
                    self.tag = selected_tag
                    self.update()
                    editor.data_changed.emit()

        super().mouseDoubleClickEvent(event)


class LadderRungItem(QGraphicsRectItem):
    """A single rung in the ladder diagram"""
    
    def __init__(self, rung_index: int, num_cells: int = 7, cell_size: QSize = QSize(120, 60)):
        super().__init__(0, 0, num_cells * cell_size.width() + 40 + NUMBER_GUTTER, cell_size.height() + 20)
        self.rung_index = rung_index
        self.num_cells = num_cells
        self.cell_size = cell_size
        self.cells: List[LadderCellItem] = []
        
        # No visible rung box - real ladder software separates rungs with
        # spacing alone, not a bordered frame around each one.
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(-2)
        
        # Enable selection
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # Create cells
        self._create_cells()

        # Draw power rails
        self._draw_power_rails()

        # Rung number label, shown to the left of the rung
        self.number_label = QGraphicsTextItem(self)
        font = QFont()
        font.setPointSize(9)
        self.number_label.setFont(font)
        self.number_label.setDefaultTextColor(QColor(120, 120, 120))
        self._reposition_number_label()

    def _reposition_number_label(self):
        """Keep the rung number aligned to the left of the power rail"""
        self.number_label.setPlainText(str(self.rung_index + 1))
        self.number_label.setPos(4, self.rect().height() / 2 - 10)

    def set_rung_index(self, index: int):
        """Update this rung's index and refresh its number label"""
        self.rung_index = index
        for cell in self.cells:
            cell.row = index
        self._reposition_number_label()
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        menu = QMenu()
        
        insert_above_action = menu.addAction("Insert Rung Above")
        insert_below_action = menu.addAction("Insert Rung Below")
        menu.addSeparator()
        delete_action = menu.addAction("Delete Rung")
        
        action = menu.exec(event.screenPos())
        
        if action == insert_above_action:
            self.scene().parent_widget().insert_rung(self.rung_index)
        elif action == insert_below_action:
            self.scene().parent_widget().insert_rung(self.rung_index + 1)
        elif action == delete_action:
            self.scene().parent_widget().delete_rung(self.rung_index)
    
    def _create_cells(self):
        """Create grid cells for this rung"""
        start_x = 20 + NUMBER_GUTTER  # After rung number gutter + left power rail
        start_y = 10

        for col in range(self.num_cells):
            cell = LadderCellItem(self.rung_index, col, self.cell_size)
            cell.setPos(start_x + col * self.cell_size.width(), start_y)
            cell.setParentItem(self)  # Set as child item, will be added to scene when rung is added
            self.cells.append(cell)

    def _draw_power_rails(self):
        """Draw vertical power rails"""
        rect = self.rect()

        # Left power rail
        left_rail = QGraphicsLineItem(10 + NUMBER_GUTTER, 0, 10 + NUMBER_GUTTER, rect.height(), self)
        left_rail.setPen(QPen(QColor(0, 0, 0), 3))  # Black for power rails
        # No right-hand rail - real ladder diagrams (e.g. WPLSoft) only draw
        # the left bus bar; the rung's wire simply ends at the right edge.
    
    def _redraw_power_rails(self):
        """Redraw power rails after resize"""
        # Remove existing power rail items
        for child in self.childItems():
            if isinstance(child, QGraphicsLineItem):
                self.scene().removeItem(child)
        
        # Redraw
        self._draw_power_rails()
    
    def paint(self, painter, option, widget):
        """Custom paint to show selection highlight"""
        # Draw default
        super().paint(painter, option, widget)
        
        # Draw selection highlight
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor(0, 100, 255), 2))  # Blue outline
            painter.setBrush(QBrush(QColor(200, 220, 255, 100)))  # Light blue fill with transparency
            painter.drawRect(self.rect())
    
    def get_cell(self, col: int) -> Optional[LadderCellItem]:
        """Get cell at column"""
        if 0 <= col < len(self.cells):
            return self.cells[col]
        return None
    
    def get_data(self) -> Dict[str, Any]:
        """Get rung data for serialization"""
        cells_data = []
        for cell in self.cells:
            if cell.element_type:
                cells_data.append({
                    "type": cell.element_type,
                    "tag": cell.tag
                })
            else:
                cells_data.append(None)
        
        return {
            "cells": cells_data
        }
    
    def set_data(self, data: Dict[str, Any]):
        """Set rung data from deserialization"""
        cells_data = data.get("cells", [])
        
        for col, cell_data in enumerate(cells_data):
            cell = self.get_cell(col)
            if cell and cell_data:
                cell.set_element(cell_data["type"], cell_data["tag"])


class LadderToolboxItem(QLabel):
    """Draggable item in the toolbox"""
    
    def __init__(self, element_type: str, display_name: str, icon: str):
        super().__init__(icon + " " + display_name)
        self.element_type = element_type
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("")  # Reset to default system palette
        self.setMargin(5)
    
    def mousePressEvent(self, event):
        """Start drag operation"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Create mime data explicitly
            mime_data = QMimeData()
            mime_data.setData("application/x-ladder-element", self.element_type.encode("utf-8"))
            
            # Create and configure drag
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Set drag pixmap
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            drag.exec(Qt.DropAction.CopyAction)


class LadderToolbox(QWidget):
    """Toolbox panel with draggable ladder elements"""
    
    def __init__(self):
        super().__init__()
        self.setFixedWidth(150)
        self.setStyleSheet("")  # Reset to default system palette
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Toolbox")
        title.setStyleSheet("font-weight: bold; font-size: 12pt;")  # Only font styling, no background/text color
        layout.addWidget(title)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("")  # Reset to default
        layout.addWidget(separator)
        
        # New Rung button
        self.new_rung_btn = QPushButton("+ New Rung")
        self.new_rung_btn.setFixedHeight(40)
        self.new_rung_btn.setStyleSheet("")  # Reset to default system palette
        layout.addWidget(self.new_rung_btn)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("")  # Reset to default
        layout.addWidget(separator2)
        
        # Draggable elements
        elements = [
            ("contact_no", "NO Contact", "[  ]"),
            ("contact_nc", "NC Contact", "[/ ]"),
            ("coil", "Coil", "(  )"),
            ("timer_ton", "TON Timer", "[TON]"),
        ]
        
        for element_type, display_name, icon in elements:
            item = LadderToolboxItem(element_type, display_name, icon)
            layout.addWidget(item)
        
        layout.addStretch()
        self.setLayout(layout)


class TimerConfigDialog(QDialog):
    """Dialog for configuring timer parameters"""
    
    def __init__(self, current_tag: str = "T1", current_pt: int = 1000, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Timer")
        self.setModal(True)
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        # Timer Name
        name_label = QLabel("Timer Name:")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit(current_tag)
        layout.addWidget(self.name_input)
        
        # Preset Time
        pt_label = QLabel("Preset Time (ms):")
        layout.addWidget(pt_label)
        
        pt_layout = QHBoxLayout()
        self.pt_input = QSpinBox()
        self.pt_input.setRange(1, 3600000)
        self.pt_input.setValue(current_pt)
        pt_layout.addWidget(self.pt_input)
        
        units_label = QLabel("milliseconds")
        pt_layout.addWidget(units_label)
        pt_layout.addStretch()
        
        layout.addLayout(pt_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_config(self) -> tuple:
        """Return (tag, pt) tuple"""
        return (self.name_input.text(), self.pt_input.value())


class TagSelectionDialog(QDialog):
    """Dialog for selecting tags from configured I/O"""
    
    def __init__(self, available_tags: List[tuple], element_type: str, current_tag: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Tag")
        self.setModal(True)
        self.setFixedSize(400, 400)
        self.element_type = element_type
        self.available_tags = available_tags
        self.filtered_tags = available_tags.copy()
        
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Select Tag:")
        layout.addWidget(label)
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter tags...")
        self.search_box.textChanged.connect(self.filter_tags)
        layout.addWidget(self.search_box)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Tag Name", "Type"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.accept)
        
        # Populate table
        self.populate_table(current_tag)
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def filter_tags(self, text: str):
        """Filter tags based on search text"""
        search_text = text.lower()
        self.filtered_tags = [tag for tag in self.available_tags 
                              if search_text in tag[0].lower() or search_text in tag[1].lower()]
        self.populate_table()
    
    def populate_table(self, current_tag: str = ""):
        """Populate table with filtered tags"""
        self.table.setRowCount(0)
        
        # Filter based on element type
        type_filtered = self._filter_by_element_type(self.filtered_tags)
        
        for tag_name, tag_type in type_filtered:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Tag name
            item_name = QTableWidgetItem(tag_name)
            self.table.setItem(row, 0, item_name)
            
            # Type
            item_type = QTableWidgetItem(tag_type)
            self.table.setItem(row, 1, item_type)
            
            # Preselect current tag
            if tag_name == current_tag:
                self.table.selectRow(row)
    
    def _filter_by_element_type(self, tags: List[tuple]) -> List[tuple]:
        """Filter tags based on ladder element type"""
        readable_types = ["BOOL", "Digital Input", "Digital Output", "TON", "COUNTER", "Analog Input"]
        writable_types = ["BOOL", "Digital Output", "Analog Output"]
        timer_types = ["TON"]
        
        if self.element_type in ["contact_no", "contact_nc"]:
            # Show readable tags
            return [tag for tag in tags if tag[1] in readable_types]
        elif self.element_type == "coil":
            # Show writable tags
            return [tag for tag in tags if tag[1] in writable_types]
        elif self.element_type == "timer_ton":
            # Show timer tags only
            return [tag for tag in tags if tag[1] in timer_types]
        else:
            # Show all tags
            return tags
    
    def get_selected_tag(self) -> str:
        """Return the selected tag name"""
        selected_items = self.table.selectedItems()
        if selected_items:
            return selected_items[0].text()
        return ""


class TagEditDialog(QDialog):
    """Dialog for editing element tag names"""
    
    def __init__(self, current_tag: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Tag")
        self.setModal(True)
        self.setFixedSize(300, 100)
        
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Tag Name:")
        label.setStyleSheet("")  # Reset to default
        layout.addWidget(label)
        
        # Input
        self.input = QLineEdit(current_tag)
        self.input.setStyleSheet("")  # Reset to default
        layout.addWidget(self.input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("")  # Reset to default
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("")  # Reset to default
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        self.input.selectAll()
    
    def get_tag(self) -> str:
        """Return the entered tag name"""
        return self.input.text().strip()


class LadderGraphicsView(QGraphicsView):
    """Graphics view with middle-mouse panning and Ctrl+wheel zoom.

    Left-button drag stays reserved for drag-and-drop / item selection, so
    panning is bound to the middle mouse button instead of QGraphicsView's
    built-in ScrollHandDrag mode.
    """

    def __init__(self, scene):
        super().__init__(scene)
        self._panning = False
        self._pan_start = QPointF()
        self._zoom = 1.0

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            new_zoom = self._zoom * factor
            # Keep zoom within a sane range so the canvas can't vanish or
            # blow up past readability.
            if 0.4 <= new_zoom <= 3.0:
                self._zoom = new_zoom
                self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - int(delta.x()))
            v_bar.setValue(v_bar.value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class LadderEditorWidget(QWidget):
    """Main graphical ladder editor widget"""
    
    data_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("")  # Reset to default system palette
        
        # Data structure
        self.rungs: List[LadderRungItem] = []
        self.num_cells_per_rung = 7
        self.cell_size = QSize(MAX_CELL_WIDTH, CELL_HEIGHT)
        self.available_tags = []  # Will be populated from controller configuration
        
        # Setup UI
        self._setup_ui()
        
        # Auto-create first rung for new LAD programs
        self.add_new_rung()
    
    def set_available_tags(self, tags: List[tuple]):
        """Set the available tags from controller configuration"""
        self.available_tags = tags
    
    def get_available_tags(self) -> List[tuple]:
        """Get the available tags from controller configuration"""
        return self.available_tags
    
    def clear_editor(self):
        """Remove all existing rungs and reset the editor to a clean state."""
        self.scene.clear()
        self.rungs = []
        self.add_new_rung()
        self.data_changed.emit()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene.selectedItems()
            
            # Cell deletion takes precedence over rung deletion
            for item in selected_items:
                if isinstance(item, LadderCellItem):
                    # Clear the element and restore default wire
                    item.clear_element()
                    self.data_changed.emit()
                    event.accept()
                    return
            
            # If no cell selected, check for rung deletion
            for item in selected_items:
                if isinstance(item, LadderRungItem):
                    self.delete_rung(item.rung_index)
                    event.accept()
                    return
        super().keyPressEvent(event)
    
    def _setup_ui(self):
        """Setup the editor UI"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Toolbox
        self.toolbox = LadderToolbox()
        self.toolbox.new_rung_btn.clicked.connect(self.add_new_rung)
        main_layout.addWidget(self.toolbox)
        
        # Editor area
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # Hint bar - the interaction model (drag to place, double-click to
        # configure, middle-drag/Ctrl+wheel to navigate) isn't self-evident.
        hint = QLabel(
            "Drag an element onto a cell to place it  •  Double-click to configure  •  "
            "Delete to remove  •  Middle-drag to pan  •  Ctrl+Wheel to zoom  •  "
            "Right-click a rung to insert/delete"
        )
        hint.setStyleSheet("color: #666; padding: 4px 8px; background: #f2f2f2;")
        editor_layout.addWidget(hint)

        # Graphics view
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("white")))
        self.scene.parent_widget = self  # Reference for double-click handling

        self.view = LadderGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setStyleSheet("")  # Reset to default system palette
        # Anchor rungs to the top-left corner instead of Qt's default centered
        # placement - ladder diagrams read top-to-bottom, left-aligned.
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        editor_layout.addWidget(self.view)
        main_layout.addLayout(editor_layout)
        
        self.setLayout(main_layout)

    def showEvent(self, event):
        """Recalculate once the widget has its real, final geometry.

        The very first rung is created before this widget is embedded in the
        window's layout, when the viewport still reports a placeholder size -
        without this, cells could get stuck at the fallback minimum width.
        """
        super().showEvent(event)
        self._recalculate_rung_dimensions()

    def resizeEvent(self, event):
        """Handle window resize to recalculate rung dimensions"""
        super().resizeEvent(event)
        self._recalculate_rung_dimensions()
    
    def _recalculate_rung_dimensions(self):
        """Recalculate cell width based on available viewport width"""
        if not self.rungs:
            return
        
        # Get available width from viewport
        viewport_width = self.view.viewport().width()
        
        # Reserve margins for power rails and padding
        left_margin = 20
        right_margin = 20
        available_width = viewport_width - left_margin - right_margin
        
        # Calculate cell width dynamically, but keep it within a comfortable
        # range - narrow windows shrink cells, wide windows scroll instead of
        # stretching symbols across oversized, sparse-looking cells.
        raw_cell_width = available_width / self.num_cells_per_rung
        cell_width = max(MIN_CELL_WIDTH, min(MAX_CELL_WIDTH, raw_cell_width))

        # Update cell size
        self.cell_size = QSize(int(cell_width), CELL_HEIGHT)

        # Recalculate and update all rungs
        for rung in self.rungs:
            # Update rung rect
            rung.setRect(0, 0, self.num_cells_per_rung * self.cell_size.width() + 40 + NUMBER_GUTTER, self.cell_size.height() + 20)

            # Update cell positions and sizes
            start_x = 20 + NUMBER_GUTTER
            start_y = 10
            for col, cell in enumerate(rung.cells):
                cell.setRect(0, 0, self.cell_size.width(), self.cell_size.height())
                cell.setPos(start_x + col * self.cell_size.width(), start_y)
                # Cell will redraw itself with updated dimensions

            # Redraw power rails
            rung._redraw_power_rails()
            rung._reposition_number_label()

        # Update scene rect
        self._update_scene_rect()
    
    def add_new_rung(self):
        """Add a new empty rung"""
        rung_index = len(self.rungs)
        rung = LadderRungItem(rung_index, self.num_cells_per_rung, self.cell_size)
        
        # Recalculate dimensions to fit viewport
        self._recalculate_rung_dimensions()
        
        # Position rung below existing rungs
        y_pos = rung_index * (self.cell_size.height() + RUNG_GAP) + 20
        rung.setPos(0, y_pos)
        
        self.scene.addItem(rung)
        self.rungs.append(rung)
        
        # Update scene rect
        self._update_scene_rect()
        
        self.data_changed.emit()
    
    def _update_scene_rect(self):
        """Update scene rectangle to contain all rungs"""
        if not self.rungs:
            return
        
        max_y = max(rung.y() + rung.rect().height() for rung in self.rungs)
        max_x = max(rung.rect().width() for rung in self.rungs) if self.rungs else 800
        self.scene.setSceneRect(0, 0, max_x + 50, max_y + 50)
    
    def edit_element_tag(self, cell: LadderCellItem):
        """Open dialog to edit cell element tag"""
        dialog = TagEditDialog(cell.tag, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tag = dialog.get_tag()
            cell.tag = new_tag
            cell.update()
            self.data_changed.emit()
    
    def delete_element(self, cell: LadderCellItem):
        """Delete an element from a cell"""
        cell.clear_element()
        self.data_changed.emit()
    
    def insert_rung(self, index: int):
        """Insert a new rung at the specified index"""
        # Create new rung
        new_rung = LadderRungItem(index, self.num_cells_per_rung, self.cell_size)
        
        # Shift existing rungs down
        for i in range(index, len(self.rungs)):
            self.rungs[i].set_rung_index(i + 1)
            # Reposition
            y_pos = (i + 1) * (self.cell_size.height() + RUNG_GAP) + 20
            self.rungs[i].setPos(0, y_pos)
        
        # Insert new rung
        self.rungs.insert(index, new_rung)
        
        # Position new rung
        y_pos = index * (self.cell_size.height() + RUNG_GAP) + 20
        new_rung.setPos(0, y_pos)
        self.scene.addItem(new_rung)
        
        # Recalculate dimensions after insertion
        self._recalculate_rung_dimensions()
        
        # Update scene rect
        self._update_scene_rect()
        
        self.data_changed.emit()
    
    def delete_rung(self, index: int):
        """Delete a rung at the specified index"""
        if index < 0 or index >= len(self.rungs):
            return
        
        # Remove rung from scene
        rung = self.rungs[index]
        self.scene.removeItem(rung)
        
        # Remove from list
        self.rungs.pop(index)
        
        # Shift remaining rungs up
        for i in range(index, len(self.rungs)):
            self.rungs[i].set_rung_index(i)
            # Reposition
            y_pos = i * (self.cell_size.height() + RUNG_GAP) + 20
            self.rungs[i].setPos(0, y_pos)
        
        # Recalculate dimensions after deletion
        self._recalculate_rung_dimensions()
        
        # Update scene rect
        self._update_scene_rect()
        
        self.data_changed.emit()
    
    def get_ladder_data(self) -> Dict[str, Any]:
        """Get complete ladder data for serialization"""
        return {
            "rungs": [rung.get_data() for rung in self.rungs]
        }
    
    def set_ladder_data(self, data: Dict[str, Any]):
        """Set ladder data from deserialization"""
        # Clear existing rungs
        for rung in self.rungs:
            self.scene.removeItem(rung)
        self.rungs.clear()
        
        # Load rungs
        rungs_data = data.get("rungs", [])
        for rung_index, rung_data in enumerate(rungs_data):
            rung = LadderRungItem(rung_index, self.num_cells_per_rung, self.cell_size)
            rung.set_data(rung_data)
            
            y_pos = rung_index * (self.cell_size.height() + RUNG_GAP) + 20
            rung.setPos(0, y_pos)
            
            self.scene.addItem(rung)
            self.rungs.append(rung)
        
        self._update_scene_rect()
    
    def to_ladder_text(self) -> str:
        """Convert graphical ladder to text syntax"""
        lines = []
        
        for rung in self.rungs:
            # Build list of contacts, timers, and find coil
            contacts = []
            coil_tag = None
            timer_data = None  # (tag, pt)
            
            for cell in rung.cells:
                if cell.element_type is not None:
                    if cell.element_type == "contact_no":
                        contacts.append(cell.tag)
                    elif cell.element_type == "contact_nc":
                        contacts.append(f"!{cell.tag}")
                    elif cell.element_type == "timer_ton":
                        timer_data = (cell.tag, cell.pt)
                    elif cell.element_type == "coil":
                        coil_tag = cell.tag
            
            # Generate timer rung if timer present
            if timer_data:
                timer_tag, timer_pt = timer_data
                if contacts:
                    condition = " & ".join(contacts)
                    text = f"{condition} -> TON({timer_tag}, {timer_pt})"
                else:
                    text = f"-> TON({timer_tag}, {timer_pt})"
                lines.append(text)
                
                # Timer output can be used as a contact, so continue with coil if present
                # Reset contacts and use timer tag as a contact for the coil rung
                contacts = [timer_tag]
            
            # Only add coil rung if it has a coil
            if coil_tag is not None:
                if contacts:
                    condition = " & ".join(contacts)
                    text = f"{condition} -> {coil_tag}"
                else:
                    text = f"-> {coil_tag}"
                lines.append(text)
            
            # If there are no coils but there are contacts (rung without output), ignore it
            # This handles the case where we have a timer rung that was already added above
        
        return "\n".join(lines)
    
    def from_ladder_text(self, text: str):
        """Convert text syntax to graphical ladder"""
        # Always start from a blank editor
        self.clear_editor()
        
        if not text or not text.strip():
            return
        
        # Parse text and create rungs
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        for line in lines:
            rung_index = len(self.rungs)
            rung = LadderRungItem(rung_index, self.num_cells_per_rung, self.cell_size)
            
            # Parse line (simple parsing for now)
            # Format: "tag1 & tag2 -> output" or "!tag1 & tag2 -> output"
            # Format: "tag1 & tag2 -> TON(T1, 5000)"
            parts = line.split("->")
            if len(parts) == 2:
                condition = parts[0].strip()
                output = parts[1].strip()
                
                # Check if output is a timer function
                timer_match = None
                if output.startswith("TON(") and output.endswith(")"):
                    # Parse TON(T1, 5000)
                    import re
                    timer_match = re.match(r'TON\((\w+),\s*(\d+)\)', output)
                
                if timer_match:
                    # Timer output
                    timer_tag = timer_match.group(1)
                    timer_pt = int(timer_match.group(2))
                    
                    # Parse condition
                    tags = []
                    for tag in condition.split("&"):
                        tag = tag.strip()
                        if tag.startswith("!"):
                            tags.append(("contact_nc", tag[1:]))
                        else:
                            tags.append(("contact_no", tag))
                    
                    # Place elements in cells
                    for col, (element_type, tag) in enumerate(tags):
                        cell = rung.get_cell(col)
                        if cell:
                            cell.set_element(element_type, tag)
                    
                    # Place timer
                    timer_col = len(tags)
                    cell = rung.get_cell(timer_col)
                    if cell:
                        cell.set_element("timer_ton", timer_tag, timer_pt)
                else:
                    # Normal coil output
                    # Parse condition
                    tags = []
                    for tag in condition.split("&"):
                        tag = tag.strip()
                        if tag.startswith("!"):
                            tags.append(("contact_nc", tag[1:]))
                        else:
                            tags.append(("contact_no", tag))
                    
                    # Place elements in cells
                    for col, (element_type, tag) in enumerate(tags):
                        cell = rung.get_cell(col)
                        if cell:
                            cell.set_element(element_type, tag)
                    
                    # Place coil
                    coil_col = len(tags)
                    cell = rung.get_cell(coil_col)
                    if cell:
                        cell.set_element("coil", output)
            
            y_pos = rung_index * (self.cell_size.height() + RUNG_GAP) + 20
            rung.setPos(0, y_pos)
            
            self.scene.addItem(rung)
            self.rungs.append(rung)
        
        self._update_scene_rect()
