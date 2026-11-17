"""Comprobación funcional de Qt sin requerir un escritorio visible."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from app.core.models import Status
from app.ui.iteration_table import format_number


@pytest.fixture
def window():
    application = QApplication.instance() or QApplication([])
    instance = MainWindow()
    instance.show()
    application.processEvents()
    yield instance
    instance.close()
    application.processEvents()


def test_window_calculation_validation_and_invalidation():
    application = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    application.processEvents()
    assert window.isVisible()
    window.calculate_button.click()
    assert window.status.text() == "Convergencia alcanzada"
    assert "1.41421356237" in window.answer.text()
    assert "2*x" in window.derivative_label.text()
    window.initial.setText("0")
    assert window.answer.text() == "—"
    window.calculate_button.click()
    assert window.status.text() == "Derivada nula o casi nula"
    window.function.setText("log(x)")
    window.initial.setText("-1")
    window.calculate_button.click()
    assert window.status.text() == "Error de dominio"
    window.function.setText("x +")
    window.calculate_button.click()
    assert window.status.text() == "Revisá los parámetros"
    assert window.answer.text() == "—"
    window.function.setText("x**2 - 2")
    window.initial.setText("abc")
    window.calculate_button.click()
    assert "deben ser números" in window.details.text()
    window.close()


def test_table_replacement_error_and_clear(window):
    window.calculate()
    original = window.current_result
    assert window.table_model.iterations == original.iterations
    assert window.table_stack.currentWidget() is window.table
    window.function.setText("cos(x) - x")
    assert window.current_result is None
    assert window.table_model.rowCount() == 0
    window.calculate()
    assert window.current_result is not original
    assert window.table_model.iterations == window.current_result.iterations
    window.function.setText("log(x)")
    window.initial.setText("-1")
    window.calculate()
    assert window.current_result.status is Status.DOMAIN_ERROR
    assert window.table_model.rowCount() == 0
    assert window.table_stack.currentWidget() is window.table_empty
    assert window.state_badge.text() == "Error matemático"
    window.clear_button.click()
    assert window.function.text() == ""
    assert window.initial.text() == "1.5"
    assert window.tolerance.text() == "1e-8"
    assert window.maximum.value() == 100
    assert window.current_result is None
    assert window.answer.text() == "—"
    assert window.function_value.text() == "—"
    assert window.expression_label.toolTip() == ""
    assert window.table_model.rowCount() == 0
    assert window.state_badge.text() == "Listo"


@pytest.mark.parametrize("name, text", [("function", "x +"), ("initial", "abc"),
                                       ("initial", "inf"), ("tolerance", "nan"),
                                       ("tolerance", "0"), ("tolerance", "-1")])
def test_validation_is_near_the_invalid_field(window, name, text):
    window.calculate()
    field = getattr(window, name)
    field.setText(text)
    window.calculate()
    assert field.property("invalid") is True
    assert window.field_errors[field].isVisible()
    assert window.current_result is None
    assert window.table_model.rowCount() == 0
    assert window.answer.text() == "—"
    assert window.function_value.text() == "—"
    window.clear_button.click()
    assert not field.property("invalid")
    assert not window.field_errors[field].isVisible()


def test_many_iterations_scrolling_selection_and_copy(window):
    window.function.setText("x**3 - 2*x + 2")
    window.initial.setText("0")
    window.maximum.setValue(1000)
    window.calculate()
    QApplication.processEvents()
    assert window.current_result.status is Status.MAX_ITERATIONS
    assert window.state_badge.text() == "No convergente"
    assert window.table_model.rowCount() == 1000
    assert window.table.verticalScrollBar().maximum() > 0
    selected = []
    window.iteration_selected.connect(selected.append)
    window.table.selectRow(999)
    window.table.scrollToBottom()
    QApplication.processEvents()
    assert selected[-1] is window.current_result.iterations[-1]
    assert window.table.verticalScrollBar().value() == window.table.verticalScrollBar().maximum()
    window.table.setFocus()
    QTest.keyClick(window.table, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    columns = QApplication.clipboard().text().split("\t")
    assert columns[0] == "1000"
    assert float(columns[1]) == window.current_result.iterations[-1].x
    assert len(columns) == 6
    window.clear_button.click()
    assert selected[-1] is None


def test_signed_function_value_and_exact_initial_root(window):
    window.function.setText("x**3 - x - 2")
    window.initial.setText("1")
    window.maximum.setValue(2)
    window.calculate()
    # Lejos de convergencia, f(x) conserva su signo; no se muestra |f(x)|.
    assert window.function_value.text() == format_number(0.7453042824943643)
    window.function.setText("-x**2 + 2")
    window.initial.setText("1.5")
    window.maximum.setValue(1)
    window.calculate()
    assert window.function_value.text().startswith("-")
    window.function.setText("x**2")
    window.initial.setText("0")
    window.calculate()
    assert window.current_result.converged
    assert window.iteration_count.text() == "0"
    assert window.function_value.text() == "0"
    assert window.final_error.text() == "—"
    assert "raíz exacta" in window.table_empty.text()


def test_keyboard_and_partial_history(window):
    window.initial.setFocus()
    QTest.keyClick(window.initial, Qt.Key.Key_Return)
    assert window.current_result.converged
    window.function.setText("log(x)+10+x**2")
    window.initial.setText("10")
    window.calculate()
    assert window.current_result.status is Status.DOMAIN_ERROR
    assert len(window.current_result.iterations) > 0
    assert window.table_model.iterations == window.current_result.iterations
    QTest.keyClick(window, Qt.Key.Key_L, Qt.KeyboardModifier.ControlModifier)
    assert window.current_result is None
    assert window.function.text() == ""


@pytest.mark.parametrize("width, height", [(900, 700), (1240, 860), (1600, 1000)])
def test_adaptable_layout(window, width, height):
    window.resize(width, height)
    window.calculate()
    QApplication.processEvents()
    assert window.size().width() == width
    assert window.size().height() == height
    assert window.canvas.width() > window.parameter_scroll.width()
    assert window.canvas.height() >= 140
    assert window.table.viewport().height() > 0
    assert window.parameter_scroll.widget().width() <= window.parameter_scroll.viewport().width()
