import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui import theme
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    resolved_mode = theme.resolve_mode(theme.load_saved_mode(), app)
    theme.apply_theme(app, resolved_mode)
    window = MainWindow(resolved_mode)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
