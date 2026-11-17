import csv
import os
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from pypdf import PdfReader
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from app.core.expression_parser import parse_expression
from app.core.newton_raphson import solve
from app.services.history_service import Calculation, HistoryService, HistoryError
from app.services.export_service import export_csv, export_pdf, ExportError, CSV_HEADERS
from app.data.examples import EXAMPLES
from app.ui.main_window import MainWindow
from app.ui.history_dialog import HistoryDialog
from app.ui.theme import COLORS


def calculation(function="x**2 - 2", x0=1.5, maximum=100):
    parsed = parse_expression(function)
    return Calculation(function, str(parsed.derivative), x0, 1e-8, maximum, solve(parsed, x0, 1e-8, maximum))


def test_history_roundtrip_search_delete_and_clear(tmp_path):
    history = HistoryService(tmp_path / "user" / "history.sqlite3")
    assert history.recent() == []
    calc = calculation()
    identifier = history.save(calc)
    record = HistoryService(history.path).get(identifier)
    assert record.function == calc.function
    assert record.derivative == calc.derivative
    assert record.x0 == calc.x0
    assert record.tolerance == calc.tolerance
    assert record.max_iterations == calc.max_iterations
    assert record.root == calc.result.root
    assert record.iteration_count == len(calc.result.iterations)
    assert record.created_at.endswith("+00:00")
    assert len(history.recent("x**2")) == 1
    assert history.recent("%' OR 1=1 --") == []
    assert history.recent("cos") == []
    failed = history.save(calculation("x**3-2*x+2", 0, 8))
    assert history.get(failed).root is None
    history.delete(identifier)
    assert history.get(identifier) is None
    history.clear()
    assert history.recent() == []


def test_corrupt_history_is_a_controlled_error(tmp_path):
    path = tmp_path / "invalid.db"
    path.write_bytes(b"not a database")
    with pytest.raises(HistoryError):
        HistoryService(path).recent()


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.title)
def test_examples_have_valid_initial_points_and_converge(example):
    result = solve(example.function, example.x0, example.tolerance, example.max_iterations)
    assert result.converged


@pytest.mark.parametrize("function, x0, maximum", [("x**2-2", 1.5, 100), ("x**3-2*x+2", 0, 100)])
def test_csv_roundtrip(tmp_path, function, x0, maximum):
    calc = calculation(function, x0, maximum)
    path = tmp_path / "result.csv"
    export_csv(calc, path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == list(CSV_HEADERS)
    assert len(rows) == len(calc.result.iterations) + 1
    for row, step in zip(rows[1:], calc.result.iterations):
        assert int(row[0]) == step.index
        assert [float(v) for v in row[1:]] == [step.x, step.fx, step.derivative, step.next_x, step.absolute_error]


def test_empty_csv_does_not_create_file(tmp_path):
    target = tmp_path / "empty.csv"
    with pytest.raises(ExportError, match="No hay iteraciones"):
        export_csv(calculation("x**2", 0), target)
    assert not target.exists()


@pytest.mark.parametrize("function, x0, maximum", [("x**2-2", 1.5, 100), ("x**3-2*x+2", 0, 120), ("log(x)", -1, 100), ("x**2", 0, 100)])
def test_pdf_contents_multipage_and_failure(tmp_path, function, x0, maximum):
    calc = calculation(function, x0, maximum)
    path = tmp_path / "report.pdf"
    export_pdf(calc, path, COLORS)
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) >= 2
    assert "NewtonLab" in text
    assert function in text
    assert calc.derivative in text
    assert calc.result.status.value in text
    assert "Residuo absoluto" in text
    assert "x_(n+1)" in text
    assert len(reader.pages[0].images) == 1
    if calc.result.converged:
        assert "Raíz aproximada:" in text
    else:
        assert "No se obtuvo una raíz con convergencia confirmada." in text
        assert "Raíz aproximada:" not in text
    if maximum == 120:
        assert len(reader.pages) >= 4
        for page in reader.pages[1:]:
            assert "Error absoluto" in page.extract_text()
        assert "120" in reader.pages[-1].extract_text()


@pytest.mark.parametrize("kind", ["csv", "pdf"])
def test_export_write_error_preserves_existing_target(tmp_path, kind):
    target = tmp_path / "directory"
    target.mkdir()
    with pytest.raises(ExportError):
        if kind == "csv":
            export_csv(calculation(), target)
        else:
            export_pdf(calculation(), target, COLORS)
    assert target.is_dir()
    assert list(tmp_path.glob(".newtonlab-*")) == []


@pytest.fixture
def window(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    instance = MainWindow(HistoryService(tmp_path / "history.sqlite3"))
    instance.show()
    application.processEvents()
    yield instance
    instance.close()
    application.processEvents()


def test_restore_does_not_duplicate_and_updates_plot(window):
    window.calculate()
    window.save_current()
    window.save_current()
    entries = window.history_service.recent()
    assert len(entries) == 1
    window.reset()
    window.restore_history(entries[0])
    assert len(window.history_service.recent()) == 1
    assert window.function.text() == entries[0].function
    assert window.current_result.converged
    assert window.table_model.iterations == window.current_result.iterations
    assert window.plot_widget.result is window.current_result
    assert not window.save_action.isEnabled()


def test_example_loading_does_not_calculate_or_save(window):
    window.calculate()
    window.load_example(6)
    assert window.function.text() == "log(x) - 1"
    assert float(window.initial.text()) == 2
    assert float(window.tolerance.text()) == 1e-8
    assert window.current_result is None
    assert window.plot_widget.result is None
    assert window.table_model.rowCount() == 0
    assert window.example_description.text()
    assert window.history_service.recent() == []
    assert not window.pdf_action.isEnabled()


def test_history_dialog_search_open_delete_and_confirmation(window, monkeypatch):
    window.calculate()
    window.save_current()
    dialog = HistoryDialog(window.history_service, window)
    assert dialog.table.rowCount() == 1
    dialog.search.setText("cos")
    dialog.refresh()
    assert dialog.table.rowCount() == 0
    dialog.search.clear()
    dialog.refresh()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    dialog.clear_history()
    assert len(window.history_service.recent()) == 1
    dialog.table.selectRow(0)
    dialog.open_selected()
    assert dialog.selected_entry.function == window.function.text()
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    dialog.delete_selected()
    assert window.history_service.recent() == []
    window.history_service.save(window.current_calculation)
    dialog.clear_history()
    assert window.history_service.recent() == []
    dialog.close()


def test_pdf_export_does_not_alter_canvas_or_selection(window, tmp_path, monkeypatch):
    window.calculate()
    plot = window.plot_widget
    plot.navigate(1)
    plot.axes.set_xlim(.8, 1.8)
    before = (plot.axes.get_xlim(), plot.axes.get_ylim(), plot.current_index, window.table.currentIndex().row())
    path = tmp_path / "report.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), ""))
    window.export_current("pdf")
    assert path.exists()
    assert before == (plot.axes.get_xlim(), plot.axes.get_ylim(), plot.current_index, window.table.currentIndex().row())


def test_export_cancel_and_empty_csv(window, tmp_path, monkeypatch):
    window.calculate()
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: ("", ""))
    window.export_current("csv")
    window.function.setText("x**2")
    window.initial.setText("0")
    window.calculate()
    def must_not_open(*args, **kwargs):
        raise AssertionError("No se debe pedir destino para un CSV vacío")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", must_not_open)
    window.export_current("csv")
