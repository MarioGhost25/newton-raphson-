import sys
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("NewtonLab")
    application.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
