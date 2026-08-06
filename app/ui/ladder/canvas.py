"""Graphical ladder canvas. Interaction model follows what real ladder
editors (LDmicro, and the old LadderApp/WinForms project) converge on:
click to select exactly one contact/coil, then Insert Left/Right (series,
same branch) or Insert Above/Below (new parallel branch) relative to that
selection - rather than drag-and-drop from a toolbox. Right-clicking empty
rung space (nothing selected there yet) offers the simpler "Add Contact/
Add Branch/Add Coil" fallback for a still-empty rung.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.ui.ladder.model import (
    Branch,
    Contact,
    JsrCoil,
    OutputCoil,
    Rung,
    TimerCoil,
    flatten_program,
    parse_program,
)

CONTACT_SLOT_WIDTH = 100
COIL_SLOT_WIDTH = 100
ROW_HEIGHT = 64
ROW_LABEL_HEIGHT = 20  # height reserved for the tag-label box above each wire
# Vertical position of the wire itself within a row's local (0..ROW_HEIGHT)
# space - shared by ContactItem, CoilItem, and RungItem's own rail-drawing so
# the wire a contact/coil paints always lines up with the rail it sits on.
WIRE_Y_IN_ROW = ROW_LABEL_HEIGHT + (ROW_HEIGHT - ROW_LABEL_HEIGHT) / 2
RUNG_TOP_PAD = 16
RUNG_GAP = 22  # gap between rung cards - lets the dot grid show through
LEFT_RAIL_X = 40
COIL_GAP = 28
WIRE_COLOR = QColor("#000000")
WIRE_WIDTH = 3
RAIL_COLOR = QColor("#0033cc")
SELECTED_COLOR = QColor("#d81c1c")
TAG_LABEL_FILL = QColor("#ffe93b")
TAG_LABEL_BORDER = QColor("#8a7400")
PEG_COLOR = QColor("#1f9e3e")
CARD_BORDER_COLOR = QColor("#c7cbd1")
CARD_FILL_COLOR = QColor("#ffffff")
GRID_DOT_COLOR = QColor("#d8dce2")
GRID_SPACING = 24


# ---- small input dialogs ----

def _pick_tag(parent, title: str, current: str, available_tags: list[str] | None) -> str | None:
    if available_tags:
        items = list(dict.fromkeys([current, *available_tags])) if current else list(available_tags)
        text, ok = QInputDialog.getItem(parent, title, "Tag:", items, editable=True)
    else:
        text, ok = QInputDialog.getText(parent, title, "Tag:", QLineEdit.EchoMode.Normal, current)
    if not ok:
        return None
    text = text.strip()
    return text or None


def _pick_jsr_target(parent, current: str, program_names: list[str] | None) -> str | None:
    return _pick_tag(parent, "JSR Target", current, program_names)


class _TimerDialog(QDialog):
    def __init__(self, name: str, preset_ms: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer (TON)")
        layout = QFormLayout(self)
        self.name_input = QLineEdit(name)
        layout.addRow("Name:", self.name_input)
        self.preset_input = QSpinBox()
        self.preset_input.setRange(1, 3600000)
        self.preset_input.setValue(preset_ms)
        self.preset_input.setSuffix(" ms")
        layout.addRow("Preset:", self.preset_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> tuple[str, int]:
        return self.name_input.text().strip(), self.preset_input.value()


def _pick_timer(parent, name: str, preset_ms: int) -> tuple[str, int] | None:
    dialog = _TimerDialog(name, preset_ms, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    new_name, new_preset = dialog.values()
    return (new_name, new_preset) if new_name else None


def _pick_coil_kind(parent) -> str | None:
    kinds = ["Output Coil", "Timer (TON)", "JSR (Call Sub Program)"]
    choice, ok = QInputDialog.getItem(parent, "Add Coil", "Type:", kinds, editable=False)
    if not ok:
        return None
    return {"Output Coil": "output", "Timer (TON)": "timer", "JSR (Call Sub Program)": "jsr"}[choice]


# ---- symbols ----

class ContactItem(QGraphicsItem):
    """A single NO contact: --| |--, tag label above."""

    def __init__(self, rung_item: "RungItem", branch_idx: int, contact_idx: int):
        super().__init__(rung_item)
        self.rung_item = rung_item
        self.branch_idx = branch_idx
        self.contact_idx = contact_idx
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def contact(self) -> Contact:
        return self.rung_item.rung.branches[self.branch_idx].contacts[self.contact_idx]

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, CONTACT_SLOT_WIDTH, ROW_HEIGHT)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        w = CONTACT_SLOT_WIDTH
        y = WIRE_Y_IN_ROW
        x1, x2 = w * 0.32, w * 0.68
        bar_half = 13

        # Tag label sits in a filled yellow box tucked directly against
        # the symbol - not floating text with a gap above it.
        label_rect = QRectF(x1 - 6, y - ROW_LABEL_HEIGHT - 14, (x2 - x1) + 12, ROW_LABEL_HEIGHT)
        painter.setPen(QPen(SELECTED_COLOR if self.isSelected() else TAG_LABEL_BORDER, 1))
        painter.setBrush(QBrush(SELECTED_COLOR.lighter(170) if self.isSelected() else TAG_LABEL_FILL))
        painter.drawRect(label_rect)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#0a0a0a")))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self.contact().tag)

        wire_pen = QPen(SELECTED_COLOR if self.isSelected() else WIRE_COLOR, WIRE_WIDTH)
        painter.setPen(wire_pen)
        painter.drawLine(QPointF(0, y), QPointF(x1, y))
        painter.drawLine(QPointF(x2, y), QPointF(w, y))
        painter.drawLine(QPointF(x1, y - bar_half), QPointF(x1, y + bar_half))
        painter.drawLine(QPointF(x2, y - bar_half), QPointF(x2, y + bar_half))

        # Solid green connector pegs at both wire junctions - makes the
        # symbol read as anchored hardware rather than a thin floating line.
        painter.setBrush(QBrush(SELECTED_COLOR if self.isSelected() else PEG_COLOR))
        painter.setPen(Qt.PenStyle.NoPen)
        for peg_x in (0, w):
            painter.drawRect(QRectF(peg_x - 3, y - 3, 6, 6))

    def mouseDoubleClickEvent(self, event) -> None:
        self.rung_item.edit_contact(self.branch_idx, self.contact_idx)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()
        insert_left = menu.addAction("Insert Contact Left")
        insert_right = menu.addAction("Insert Contact Right")
        menu.addSeparator()
        insert_above = menu.addAction("Insert Branch Above")
        insert_below = menu.addAction("Insert Branch Below")
        menu.addSeparator()
        edit_action = menu.addAction("Edit Tag")
        delete_action = menu.addAction("Delete")

        action = menu.exec(event.screenPos())
        if action == insert_left:
            self.rung_item.insert_contact(self.branch_idx, self.contact_idx)
        elif action == insert_right:
            self.rung_item.insert_contact(self.branch_idx, self.contact_idx + 1)
        elif action == insert_above:
            self.rung_item.insert_branch(self.branch_idx)
        elif action == insert_below:
            self.rung_item.insert_branch(self.branch_idx + 1)
        elif action == edit_action:
            self.rung_item.edit_contact(self.branch_idx, self.contact_idx)
        elif action == delete_action:
            self.rung_item.delete_contact(self.branch_idx, self.contact_idx)


class CoilItem(QGraphicsItem):
    """A rung's output: plain coil, a TON timer block, or a JSR call block."""

    def __init__(self, rung_item: "RungItem", coil_idx: int):
        super().__init__(rung_item)
        self.rung_item = rung_item
        self.coil_idx = coil_idx
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

    def coil(self):
        return self.rung_item.rung.coils[self.coil_idx]

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, COIL_SLOT_WIDTH, ROW_HEIGHT)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        coil = self.coil()
        w = COIL_SLOT_WIDTH
        y = WIRE_Y_IN_ROW
        pen_color = SELECTED_COLOR if self.isSelected() else WIRE_COLOR

        if isinstance(coil, OutputCoil):
            x1, x2 = w * 0.42, w * 0.58
            radius = 13.0

            label_rect = QRectF(x1 - radius - 6, y - ROW_LABEL_HEIGHT - 14, (x2 - x1) + 2 * radius + 12, ROW_LABEL_HEIGHT)
            painter.setPen(QPen(SELECTED_COLOR if self.isSelected() else TAG_LABEL_BORDER, 1))
            painter.setBrush(QBrush(SELECTED_COLOR.lighter(170) if self.isSelected() else TAG_LABEL_FILL))
            painter.drawRect(label_rect)
            font = QFont()
            font.setPointSize(9)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#0a0a0a")))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, coil.tag)

            painter.setPen(QPen(pen_color, WIRE_WIDTH))
            painter.drawLine(QPointF(0, y), QPointF(x1 - radius, y))
            painter.drawLine(QPointF(x2 + radius, y), QPointF(w, y))
            painter.drawArc(QRectF(x1 - radius, y - 12, radius * 2, 24), 90 * 16, 180 * 16)
            painter.drawArc(QRectF(x2 - radius, y - 12, radius * 2, 24), -90 * 16, 180 * 16)

            painter.setBrush(QBrush(pen_color))
            painter.setPen(Qt.PenStyle.NoPen)
            for peg_x in (0, w):
                painter.drawRect(QRectF(peg_x - 3, y - 3, 6, 6))
        else:
            block = QRectF(w * 0.06, y - 15, w * 0.88, 30)
            painter.setPen(QPen(pen_color, WIRE_WIDTH))
            painter.drawLine(QPointF(0, y), QPointF(block.left(), y))
            painter.drawLine(QPointF(block.right(), y), QPointF(w, y))
            painter.setBrush(QBrush(pen_color))
            painter.setPen(Qt.PenStyle.NoPen)
            for peg_x in (0, w):
                painter.drawRect(QRectF(peg_x - 3, y - 3, 6, 6))

            painter.setPen(QPen(TAG_LABEL_BORDER, 2))
            painter.setBrush(QBrush(TAG_LABEL_FILL))
            painter.drawRect(block)
            painter.setPen(QPen(QColor("#0a0a0a")))
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            if isinstance(coil, TimerCoil):
                label = f"TON {coil.name}\n{coil.preset_ms}ms"
            elif isinstance(coil, JsrCoil):
                label = f"JSR\n{coil.name}"
            else:
                label = "?"
            painter.drawText(block, Qt.AlignmentFlag.AlignCenter, label)

    def mouseDoubleClickEvent(self, event) -> None:
        self.rung_item.edit_coil(self.coil_idx)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu()
        edit_action = menu.addAction("Edit")
        add_action = menu.addAction("Add Coil")
        delete_action = menu.addAction("Delete")

        action = menu.exec(event.screenPos())
        if action == edit_action:
            self.rung_item.edit_coil(self.coil_idx)
        elif action == add_action:
            self.rung_item.add_coil()
        elif action == delete_action:
            self.rung_item.delete_coil(self.coil_idx)


class RungItem(QGraphicsItem):
    """One rung: power rails, N parallel branches of contacts, N coils."""

    def __init__(self, canvas: "LadderCanvas", rung: Rung, index: int):
        super().__init__()
        self.canvas = canvas
        self.rung = rung
        self.index = index
        self._contact_items: list[list[ContactItem]] = []
        self._coil_items: list[CoilItem] = []
        self._width = 0.0
        self._height = 0.0
        self.relayout()

    # ---- layout ----

    def relayout(self) -> None:
        for row in self._contact_items:
            for item in row:
                item.setParentItem(None)
        for item in self._coil_items:
            item.setParentItem(None)
        self._contact_items = []
        self._coil_items = []

        branch_count = len(self.rung.branches)
        coil_count = len(self.rung.coils)
        max_contacts = max((len(b.contacts) for b in self.rung.branches), default=0)
        merge_x = LEFT_RAIL_X + max(max_contacts, 1) * CONTACT_SLOT_WIDTH

        for branch_idx, branch in enumerate(self.rung.branches):
            row_items = []
            y = RUNG_TOP_PAD + branch_idx * ROW_HEIGHT
            for contact_idx, _contact in enumerate(branch.contacts):
                item = ContactItem(self, branch_idx, contact_idx)
                item.setPos(LEFT_RAIL_X + contact_idx * CONTACT_SLOT_WIDTH, y)
                row_items.append(item)
            self._contact_items.append(row_items)

        for coil_idx, _coil in enumerate(self.rung.coils):
            item = CoilItem(self, coil_idx)
            y = RUNG_TOP_PAD + coil_idx * ROW_HEIGHT
            item.setPos(merge_x + COIL_GAP, y)
            self._coil_items.append(item)

        self._width = merge_x + COIL_GAP + max(coil_count, 1) * COIL_SLOT_WIDTH + 20
        self._height = max(1, branch_count, coil_count) * ROW_HEIGHT + RUNG_TOP_PAD * 2
        self._merge_x = merge_x
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        rail_pen = QPen(RAIL_COLOR, WIRE_WIDTH + 1)
        painter.setPen(rail_pen)

        branch_count = len(self.rung.branches)
        top_y = RUNG_TOP_PAD + WIRE_Y_IN_ROW
        bottom_y = RUNG_TOP_PAD + (branch_count - 1) * ROW_HEIGHT + WIRE_Y_IN_ROW

        # Left power rail spanning every branch row.
        painter.drawLine(QPointF(LEFT_RAIL_X, top_y), QPointF(LEFT_RAIL_X, bottom_y))

        # Per-branch wire from the last contact across to the merge point.
        # Contacts paint their own wire stubs with a gap at the bars, so
        # this must stop at the last contact rather than spanning the
        # whole branch - otherwise it shows straight through every
        # contact's gap and the open-circuit break disappears visually.
        wire_pen = QPen(WIRE_COLOR, WIRE_WIDTH)
        painter.setPen(wire_pen)
        for branch_idx, branch in enumerate(self.rung.branches):
            y = RUNG_TOP_PAD + branch_idx * ROW_HEIGHT + WIRE_Y_IN_ROW
            start_x = LEFT_RAIL_X + len(branch.contacts) * CONTACT_SLOT_WIDTH
            if start_x < self._merge_x:
                painter.drawLine(QPointF(start_x, y), QPointF(self._merge_x, y))

        # Right rail reconnecting every branch at the merge point.
        painter.setPen(rail_pen)
        painter.drawLine(QPointF(self._merge_x, top_y), QPointF(self._merge_x, bottom_y))

        # Wire from merge point into the coil column, and a coil bus if
        # there's more than one coil in parallel.
        coil_count = len(self.rung.coils)
        if coil_count:
            coil_top = RUNG_TOP_PAD + WIRE_Y_IN_ROW
            coil_bottom = RUNG_TOP_PAD + (coil_count - 1) * ROW_HEIGHT + WIRE_Y_IN_ROW
            painter.drawLine(QPointF(self._merge_x, coil_top), QPointF(self._merge_x, coil_bottom))
            painter.setPen(wire_pen)
            for coil_idx in range(coil_count):
                y = RUNG_TOP_PAD + coil_idx * ROW_HEIGHT + WIRE_Y_IN_ROW
                painter.drawLine(QPointF(self._merge_x, y), QPointF(self._merge_x + COIL_GAP, y))

        # Rung number, left of the rail, plain bold blue text.
        badge_rect = QRectF(4, top_y - 11, LEFT_RAIL_X - 10, 22)
        painter.setPen(QPen(RAIL_COLOR))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self.index + 1))

    # ---- mutation entry points (called by ContactItem/CoilItem menus) ----

    def insert_contact(self, branch_idx: int, at_index: int) -> None:
        tag = _pick_tag(self.canvas, "Insert Contact", "", self.canvas.get_available_tags())
        if tag is None:
            return
        self.rung.branches[branch_idx].contacts.insert(at_index, Contact(tag=tag))
        self.canvas.commit()

    def insert_branch(self, at_index: int) -> None:
        tag = _pick_tag(self.canvas, "Insert Branch", "", self.canvas.get_available_tags())
        if tag is None:
            return
        self.rung.branches.insert(at_index, Branch(contacts=[Contact(tag=tag)]))
        self.canvas.commit()

    def edit_contact(self, branch_idx: int, contact_idx: int) -> None:
        contact = self.rung.branches[branch_idx].contacts[contact_idx]
        tag = _pick_tag(self.canvas, "Edit Contact", contact.tag, self.canvas.get_available_tags())
        if tag is None:
            return
        contact.tag = tag
        self.canvas.commit()

    def delete_contact(self, branch_idx: int, contact_idx: int) -> None:
        branch = self.rung.branches[branch_idx]
        del branch.contacts[contact_idx]
        if not branch.contacts and len(self.rung.branches) > 1:
            del self.rung.branches[branch_idx]
        self.canvas.commit()

    def add_contact_to_branch(self, branch_idx: int) -> None:
        tag = _pick_tag(self.canvas, "Add Contact", "", self.canvas.get_available_tags())
        if tag is None:
            return
        self.rung.branches[branch_idx].contacts.append(Contact(tag=tag))
        self.canvas.commit()

    def add_branch(self) -> None:
        tag = _pick_tag(self.canvas, "Add Branch", "", self.canvas.get_available_tags())
        if tag is None:
            return
        self.rung.branches.append(Branch(contacts=[Contact(tag=tag)]))
        self.canvas.commit()

    def add_coil(self) -> None:
        kind = _pick_coil_kind(self.canvas)
        if kind is None:
            return
        if kind == "output":
            tag = _pick_tag(self.canvas, "Add Coil", "", self.canvas.get_available_tags())
            if tag is None:
                return
            self.rung.coils.append(OutputCoil(tag=tag))
        elif kind == "timer":
            result = _pick_timer(self.canvas, "T1", 1000)
            if result is None:
                return
            name, preset_ms = result
            self.rung.coils.append(TimerCoil(name=name, preset_ms=preset_ms))
        else:
            target = _pick_jsr_target(self.canvas, "", self.canvas.get_program_names())
            if target is None:
                return
            self.rung.coils.append(JsrCoil(name=target))
        self.canvas.commit()

    def edit_coil(self, coil_idx: int) -> None:
        coil = self.rung.coils[coil_idx]
        if isinstance(coil, OutputCoil):
            tag = _pick_tag(self.canvas, "Edit Coil", coil.tag, self.canvas.get_available_tags())
            if tag is None:
                return
            coil.tag = tag
        elif isinstance(coil, TimerCoil):
            result = _pick_timer(self.canvas, coil.name, coil.preset_ms)
            if result is None:
                return
            coil.name, coil.preset_ms = result
        elif isinstance(coil, JsrCoil):
            target = _pick_jsr_target(self.canvas, coil.name, self.canvas.get_program_names())
            if target is None:
                return
            coil.name = target
        self.canvas.commit()

    def delete_coil(self, coil_idx: int) -> None:
        del self.rung.coils[coil_idx]
        self.canvas.commit()

    def delete_rung(self) -> None:
        self.canvas.delete_rung(self.index)

    # ---- background (empty rung space) interaction ----

    def _branch_at_y(self, local_y: float) -> int:
        row = int((local_y - RUNG_TOP_PAD) // ROW_HEIGHT)
        return max(0, min(row, len(self.rung.branches) - 1))

    def contextMenuEvent(self, event) -> None:
        branch_idx = self._branch_at_y(event.pos().y())
        menu = QMenu()
        add_contact = menu.addAction("Add Contact")
        add_branch = menu.addAction("Add Parallel Branch")
        add_coil = menu.addAction("Add Coil")
        menu.addSeparator()
        delete_rung = menu.addAction("Delete Rung")

        action = menu.exec(event.screenPos())
        if action == add_contact:
            self.add_contact_to_branch(branch_idx)
        elif action == add_branch:
            self.add_branch()
        elif action == add_coil:
            self.add_coil()
        elif action == delete_rung:
            self.delete_rung()


class LadderGraphicsView(QGraphicsView):
    """Middle-drag pan + Ctrl+wheel zoom. Left-click stays reserved for
    selection/context menus."""

    def __init__(self, scene: QGraphicsScene):
        super().__init__(scene)
        self._panning = False
        self._pan_start = QPointF()
        self._zoom = 1.0
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """A faint dot grid over the whole visible area (not just the
        scene's content rect) so empty canvas space reads as an
        intentional engineering sheet rather than a blank void."""
        painter.fillRect(rect, QBrush(QColor("#ffffff")))
        painter.setPen(QPen(GRID_DOT_COLOR, 1.6))
        left = int(rect.left()) - (int(rect.left()) % GRID_SPACING)
        top = int(rect.top()) - (int(rect.top()) % GRID_SPACING)
        x = left
        while x < rect.right():
            y = top
            while y < rect.bottom():
                painter.drawPoint(QPointF(x, y))
                y += GRID_SPACING
            x += GRID_SPACING

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            new_zoom = self._zoom * factor
            if 0.4 <= new_zoom <= 3.0:
                self._zoom = new_zoom
                self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class LadderCanvas(QWidget):
    """Top-level ladder canvas widget: New Rung button + the graphics view.
    Owns the Rung list for one ProgramEntry, keeping its ladder_text in
    sync via model.flatten_program on every mutation."""

    def __init__(self, get_available_tags=None, get_program_names=None, on_changed=None, parent=None):
        super().__init__(parent)
        self._get_available_tags = get_available_tags or (lambda: [])
        self._get_program_names = get_program_names or (lambda: [])
        self._on_changed = on_changed
        self.program_entry = None
        self.rungs: list[Rung] = []
        self._rung_items: list[RungItem] = []
        self._band_items: list[QGraphicsRectItem] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        new_rung_btn = QPushButton("+ New Rung")
        new_rung_btn.clicked.connect(self.add_rung)
        toolbar.addWidget(new_rung_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QBrush(QColor("#f5f5f2")))
        self.view = LadderGraphicsView(self.scene)
        self.view.setToolTip(
            "Right-click a contact/coil to insert or delete. Double-click to edit.\n"
            "Right-click empty rung space to add the first element.\n"
            "Middle-drag to pan, Ctrl+wheel to zoom."
        )
        layout.addWidget(self.view)

    def get_available_tags(self) -> list[str]:
        return self._get_available_tags()

    def get_program_names(self) -> list[str]:
        return self._get_program_names()

    def set_project_entry(self, program_entry) -> None:
        self.program_entry = program_entry
        self.rungs = parse_program(program_entry.ladder_text)
        self._relayout_all()

    def commit(self) -> None:
        """Called by RungItem after any mutation: relayout, persist to the
        bound ProgramEntry's ladder_text, notify the host panel."""
        self._relayout_all()
        if self.program_entry is not None:
            self.program_entry.ladder_text = flatten_program(self.rungs)
        if self._on_changed is not None:
            self._on_changed()

    def add_rung(self) -> None:
        self.rungs.append(Rung(branches=[Branch(contacts=[Contact(tag="input1")])], coils=[OutputCoil(tag="output1")]))
        self.commit()

    def delete_rung(self, index: int) -> None:
        if 0 <= index < len(self.rungs):
            del self.rungs[index]
        self.commit()

    def _relayout_all(self) -> None:
        for item in self._rung_items:
            self.scene.removeItem(item)
        for item in self._band_items:
            self.scene.removeItem(item)
        self._rung_items = []
        self._band_items = []

        # First pass: build every RungItem (this computes its own height/
        # width) without adding it to the scene yet, so the background bands
        # below can be sized to the widest rung for a consistent "sheet" look
        # rather than each rung floating at its own narrower width.
        positioned = []
        y = 10
        max_width = 400.0
        for index, rung in enumerate(self.rungs):
            item = RungItem(self, rung, index)
            positioned.append((item, y))
            y += item._height + RUNG_GAP
            max_width = max(max_width, item._width)

        # Each rung gets its own bordered white "card" sized to the widest
        # rung, sitting on the dotted canvas with a visible gap between
        # cards - gives structure without the washed-out look flat
        # alternating gray bands had.
        for item, item_y in positioned:
            band = QGraphicsRectItem(0, item_y - 4, max_width + 20, item._height + 8)
            band.setBrush(QBrush(CARD_FILL_COLOR))
            band.setPen(QPen(CARD_BORDER_COLOR, 1.5))
            band.setZValue(-1)
            self.scene.addItem(band)
            self._band_items.append(band)

        for item, item_y in positioned:
            item.setPos(0, item_y)
            self.scene.addItem(item)
            self._rung_items.append(item)

        self.scene.setSceneRect(0, 0, max_width + 40, y + 40)
