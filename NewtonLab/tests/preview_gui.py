"""Verificación visual manual: python tests/preview_gui.py DIRECTORIO_DE_CAPTURAS."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()

    def capture(name, size):
        window.resize(*size)
        app.processEvents()
        window.plot_widget.canvas.draw()
        app.processEvents()
        assert window.grab().save(str(output / name))

    def verify():
        window.calculate()
        capture("fase3-normal.png", (1240, 860))
        window.plot_widget.next_button.click()
        assert window.table.currentIndex().row() == 1
        capture("fase3-compacta.png", (900, 700))
        window.function.setText("1/x - 1")
        window.initial.setText("0.25")
        window.calculate()
        capture("fase3-discontinuidad.png", (1600, 1000))
        window.function.setText("x**3-2*x+2")
        window.initial.setText("0")
        window.maximum.setValue(8)
        window.calculate()
        window.plot_widget.last_button.click()
        capture("fase3-no-convergente.png", (1240, 860))
        print("Verificación nativa completada: tres tamaños, selección sincronizada, discontinuidad y no convergencia.")
        window.close()
        app.quit()

    QTimer.singleShot(300, verify)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
