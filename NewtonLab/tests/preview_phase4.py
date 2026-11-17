"""Comprobación manual sin utilizar la base de datos real del usuario."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.history_dialog import HistoryDialog
from app.services.history_service import HistoryService
from app.services.export_service import export_pdf, export_csv
from app.ui.theme import COLORS


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyle("Fusion")
    with tempfile.TemporaryDirectory(prefix="newtonlab-qa-") as directory:
        service = HistoryService(Path(directory) / "history.sqlite3")
        window = MainWindow(service)
        window.show()
        def verify():
            window.load_example(3)
            window.calculate()
            identifier = service.save(window.current_calculation)
            window.reset()
            window.restore_history(service.get(identifier))
            assert len(service.recent()) == 1
            app.processEvents()
            window.plot_widget.canvas.draw()
            assert window.grab().save(str(output / "fase4-ventana.png"))
            export_pdf(window.current_calculation, output / "fase4-convergente.pdf", COLORS)
            export_csv(window.current_calculation, output / "fase4-iteraciones.csv")
            dialog = HistoryDialog(service, window)
            dialog.show()
            app.processEvents()
            assert dialog.grab().save(str(output / "fase4-historial.png"))
            dialog.close()
            window.resize(900, 700)
            app.processEvents()
            assert window.grab().save(str(output / "fase4-compacta.png"))
            window.function.setText("x**3-2*x+2")
            window.initial.setText("0")
            window.maximum.setValue(120)
            window.calculate()
            export_pdf(window.current_calculation, output / "fase4-multipagina.pdf", COLORS)
            print("Verificados: inicio, biblioteca, historial temporal, restauración, PDF y CSV.")
            window.close()
            app.quit()
        QTimer.singleShot(250, verify)
        return app.exec()


if __name__ == "__main__":
    sys.exit(main())
