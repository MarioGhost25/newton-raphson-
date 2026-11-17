import math
from pathlib import Path
from PySide6.QtCore import QEventLoop, Qt, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSplitter, QStackedWidget, QVBoxLayout, QWidget, QMenu, QComboBox, QFileDialog, QMessageBox, QDialog,
)
from app.core.expression_parser import ExpressionError, parse_expression
from app.core.models import Status
from app.core.newton_raphson import EvaluationError, evaluate, solve
from .iteration_table import IterationTableModel, IterationTableView, format_number
from .theme import stylesheet
from .plot_widget import PlotWidget
from app.services.history_service import Calculation, HistoryService, HistoryEntry, HistoryError
from app.services.export_service import export_csv, export_pdf, ExportError
from app.data.examples import EXAMPLES
from .history_dialog import HistoryDialog
from .theme import COLORS


class MainWindow(QMainWindow):
    # Conserva la señal pública para consumidores del historial.
    iteration_selected = Signal(object)

    def __init__(self, history_service: HistoryService | None = None):
        super().__init__()
        self.current_result = None
        self.current_calculation: Calculation | None = None
        self.history_service = history_service if history_service is not None else HistoryService()
        self.setWindowTitle("NewtonLab — Newton-Raphson")
        self.resize(1240, 860)
        self.setMinimumSize(900, 700)
        self.setStyleSheet(stylesheet())
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)
        header = QFrame(objectName="header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 12)
        header_layout.addWidget(QLabel("NewtonLab", objectName="brand"))
        header_layout.addWidget(QLabel("Método de Newton-Raphson", objectName="muted"))
        header_layout.addStretch()
        self.history_button = QPushButton("Historial")
        self.history_button.clicked.connect(self.show_history)
        header_layout.addWidget(self.history_button)
        self.actions_button = QPushButton("Acciones")
        menu = QMenu(self.actions_button)
        self.save_action = menu.addAction("Guardar cálculo")
        self.save_action.triggered.connect(self.save_current)
        self.pdf_action = menu.addAction("Exportar PDF")
        self.pdf_action.triggered.connect(lambda: self.export_current("pdf"))
        self.csv_action = menu.addAction("Exportar CSV")
        self.csv_action.triggered.connect(lambda: self.export_current("csv"))
        for action in (self.save_action, self.pdf_action, self.csv_action):
            action.setEnabled(False)
        self.actions_button.setMenu(menu)
        header_layout.addWidget(self.actions_button)
        self.state_badge = QLabel("Listo", objectName="state")
        header_layout.addWidget(self.state_badge)
        layout.addWidget(header)

        self.workspace = QSplitter(Qt.Orientation.Horizontal)
        self.workspace.setChildrenCollapsible(False)
        layout.addWidget(self.workspace, 1)
        sidebar = QFrame(objectName="sidebar")
        sidebar.setMinimumWidth(248)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(12, 12, 12, 12)
        controls.setSpacing(6)
        controls.addWidget(QLabel("PARÁMETROS", objectName="section"))
        self.examples = QComboBox()
        self.examples.addItem("Biblioteca de ejercicios…")
        self.examples.addItems([example.title for example in EXAMPLES])
        self.examples.setAccessibleName("Biblioteca de ejercicios")
        controls.addWidget(self.examples)
        self.example_description = self.selectable("")
        self.example_description.setObjectName("muted")
        self.example_description.hide()
        controls.addWidget(self.example_description)
        self.function = QLineEdit("x**2 - 2")
        self.function.setPlaceholderText("Ejemplo: x**3 - x - 2")
        self.function.setMaxLength(512)
        self.initial = QLineEdit("1.5")
        self.tolerance = QLineEdit("1e-8")
        self.maximum = QSpinBox()
        self.maximum.setRange(1, 1000)
        self.maximum.setValue(100)
        self.maximum.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        self.field_errors = {}
        for caption, field in (("Función f(x)", self.function), ("Valor inicial x₀", self.initial),
                               ("Tolerancia", self.tolerance), ("Máximo de iteraciones", self.maximum)):
            label = QLabel(caption)
            label.setBuddy(field)
            field.setAccessibleName(caption)
            controls.addWidget(label)
            controls.addWidget(field)
            error = self.selectable("")
            error.setObjectName("fieldError")
            error.hide()
            controls.addWidget(error)
            self.field_errors[field] = error
            if field is self.function:
                help_text = self.selectable("Usá * para multiplicar y ** para potencias.\nsin, cos, tan, exp, log, sqrt; pi y e.")
                help_text.setObjectName("muted")
                help_text.setToolTip("También: asin, acos, atan, sinh, cosh, tanh y abs. Ángulos en radianes; log es natural.")
                controls.addWidget(help_text)
                controls.addSpacing(8)
                controls.addWidget(QLabel("CONFIGURACIÓN DEL MÉTODO", objectName="section"))
        controls.addSpacing(8)
        self.calculate_button = QPushButton("Calcular raíz", objectName="calculate")
        self.calculate_button.setToolTip("Calcular · Ctrl+Enter")
        self.calculate_button.clicked.connect(self.calculate)
        controls.addWidget(self.calculate_button)
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.setToolTip("Limpiar el cálculo y restablecer los parámetros · Ctrl+L")
        self.clear_button.clicked.connect(self.reset)
        controls.addWidget(self.clear_button)
        controls.addStretch()
        note = self.selectable("Criterio de convergencia\nError absoluto y |f(x)| ≤ tolerancia.")
        note.setObjectName("muted")
        controls.addWidget(note)
        self.parameter_scroll = QScrollArea()
        self.parameter_scroll.setWidgetResizable(True)
        self.parameter_scroll.setMinimumWidth(270)
        self.parameter_scroll.setWidget(sidebar)
        self.workspace.addWidget(self.parameter_scroll)

        self.analysis_splitter = QSplitter(Qt.Orientation.Vertical)
        self.analysis_splitter.setChildrenCollapsible(False)
        self.workspace.addWidget(self.analysis_splitter)
        self.workspace.setStretchFactor(0, 1)
        self.workspace.setStretchFactor(1, 3)
        self.workspace.setSizes([320, 880])

        self.canvas = QFrame(objectName="canvas")
        self.canvas.setMinimumHeight(350)
        canvas_layout = QVBoxLayout(self.canvas)
        canvas_layout.setContentsMargins(10, 8, 10, 8)
        canvas_layout.addWidget(QLabel("ESPACIO MATEMÁTICO", objectName="section"))
        self.plot_host = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_host)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = PlotWidget()
        self.plot_layout.addWidget(self.plot_widget)
        self.plot_widget.index_changed.connect(self._select_plot_row)
        canvas_layout.addWidget(self.plot_host, 1)
        self.analysis_splitter.addWidget(self.canvas)

        analysis = QWidget()
        right = QVBoxLayout(analysis)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        result = QFrame(objectName="result")
        result_layout = QVBoxLayout(result)
        result_layout.setContentsMargins(14, 12, 14, 12)
        result_layout.setSpacing(5)
        result_layout.addWidget(QLabel("RESULTADO", objectName="section"))
        # Campos de solo lectura permiten recorrer expresiones largas sin ensanchar la ventana.
        self.expression_label = QLineEdit("f(x) = —", objectName="symbolic")
        self.derivative_label = QLineEdit("f′(x) = —", objectName="symbolic")
        for field in (self.expression_label, self.derivative_label):
            field.setReadOnly(True)
            result_layout.addWidget(field)
        self.answer = self.selectable("—")
        self.answer.setObjectName("answer")
        self.status = self.selectable("Listo para calcular")
        result_summary = QVBoxLayout()
        result_summary.addWidget(self.answer)
        result_summary.addWidget(self.status)
        result_layout.addLayout(result_summary)
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(18)
        self.function_value = self.selectable("—")
        self.final_error = self.selectable("—")
        self.iteration_count = self.selectable("—")
        for column, (title, label) in enumerate((("f(x) final", self.function_value),
                                                 ("Error final", self.final_error),
                                                 ("Iteraciones", self.iteration_count))):
            metrics.addWidget(QLabel(title, objectName="muted"), column, 0)
            metrics.addWidget(label, column, 1)
        metrics.setColumnStretch(1, 1)
        result_layout.addLayout(metrics)
        self.details = self.selectable("Ingresá los parámetros y calculá una raíz.")
        self.details.setObjectName("muted")
        result_layout.addWidget(self.details)
        controls.insertWidget(controls.count() - 2, result)

        procedure = QFrame(objectName="procedure")
        procedure_layout = QVBoxLayout(procedure)
        procedure_layout.setContentsMargins(0, 10, 0, 0)
        table_heading = QHBoxLayout()
        table_heading.setContentsMargins(12, 0, 12, 0)
        table_heading.addWidget(QLabel("ITERACIONES", objectName="section"))
        table_heading.addStretch()
        table_heading.addWidget(QLabel("Seleccionar filas · Ctrl+C para copiar", objectName="muted"))
        procedure_layout.addLayout(table_heading)
        self.table_model = IterationTableModel(self)
        self.table = IterationTableView()
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.table.setMinimumHeight(80)
        self.table.setModel(self.table_model)
        for column, width in enumerate((44, 130, 130, 130, 130, 130)):
            self.table.setColumnWidth(column, width)
        self.table.selectionModel().currentRowChanged.connect(self._select_iteration)
        self.table_empty = self.selectable("Todavía no hay iteraciones.\nCalculá una raíz para consultar el procedimiento.")
        self.table_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_empty.setObjectName("muted")
        self.table_stack = QStackedWidget()
        self.table_stack.setMinimumHeight(100)
        self.table_stack.addWidget(self.table_empty)
        self.table_stack.addWidget(self.table)
        procedure_layout.addWidget(self.table_stack, 1)
        right.addWidget(procedure, 1)
        # La tabla ya dispone de scroll propio; uno exterior ocultaría filas.
        self.analysis_panel = analysis
        self.analysis_panel.setMinimumHeight(150)
        self.analysis_splitter.addWidget(self.analysis_panel)
        self.analysis_splitter.setStretchFactor(0, 4)
        self.analysis_splitter.setStretchFactor(1, 1)
        self.analysis_splitter.setSizes([560, 200])
        footer = QLabel("Aritmética real · Newton-Raphson    |    Enter: calcular    ·    Ctrl+L: limpiar", objectName="muted")
        layout.addWidget(footer)

        for field in (self.function, self.initial, self.tolerance):
            field.returnPressed.connect(self.calculate)
            field.textChanged.connect(self.clear_result)
        self.maximum.valueChanged.connect(self.clear_result)
        for sequence, callback in (("Ctrl+Return", self.calculate), ("Ctrl+L", self.reset)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)
        maximum_enter = QShortcut(QKeySequence("Return"), self.maximum)
        maximum_enter.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        maximum_enter.activated.connect(self.calculate)
        self.examples.activated.connect(self.load_example)

    @staticmethod
    def selectable(text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        return label

    @Slot()
    def clear_result(self, *_):
        self.current_calculation = None
        for action in (self.save_action, self.pdf_action, self.csv_action):
            action.setEnabled(False)
        self.plot_widget.clear()
        self.current_result = None
        self.table_model.set_iterations(())
        self.iteration_selected.emit(None)
        self.table_stack.setCurrentWidget(self.table_empty)
        self.table_empty.setText("Todavía no hay iteraciones.\nCalculá una raíz para consultar el procedimiento.")
        self.answer.setText("—")
        self.status.setText("Parámetros modificados")
        self.state_badge.setText("Pendiente")
        self.details.setText("Calculá nuevamente para actualizar el resultado.")
        self.expression_label.setText("f(x) = —")
        self.derivative_label.setText("f′(x) = —")
        self.expression_label.setToolTip("")
        self.derivative_label.setToolTip("")
        for label in (self.function_value, self.final_error, self.iteration_count):
            label.setText("—")
        for field, error in self.field_errors.items():
            error.hide()
            field.setProperty("invalid", False)
            field.style().unpolish(field)
            field.style().polish(field)

    @Slot()
    def reset(self):
        self.examples.setCurrentIndex(0)
        self.example_description.clear()
        self.example_description.hide()
        self.function.clear()
        self.initial.setText("1.5")
        self.tolerance.setText("1e-8")
        self.maximum.setValue(100)
        self.clear_result()
        self.status.setText("Listo para calcular")
        self.state_badge.setText("Listo")
        self.details.setText("Ingresá los parámetros y calculá una raíz.")
        self.function.setFocus()

    def _field_error(self, field, message):
        error = self.field_errors[field]
        error.setText(message)
        error.show()
        field.setProperty("invalid", True)
        field.style().unpolish(field)
        field.style().polish(field)
        field.setFocus()
        self.parameter_scroll.ensureWidgetVisible(error)
        self.status.setText("Revisá los parámetros")
        self.state_badge.setText("Entrada inválida")
        self.details.setText(message)
        self.table_empty.setText("No hay iteraciones.\nCorregí el campo indicado y volvé a calcular.")

    @Slot()
    def calculate(self):
        self.clear_result()
        try:
            parsed = parse_expression(self.function.text())
        except ExpressionError as exc:
            self._field_error(self.function, str(exc))
            return
        values = []
        for field in (self.initial, self.tolerance):
            try:
                value = float(field.text().strip().replace(",", "."))
                if not math.isfinite(value):
                    raise ValueError
            except ValueError:
                self._field_error(field, "El valor inicial y la tolerancia deben ser números finitos; por ejemplo, 1.5 y 1e-8.")
                return
            if field is self.tolerance and value <= 0:
                self._field_error(field, "La tolerancia debe ser mayor que cero.")
                return
            values.append(value)
        self.state_badge.setText("Calculando…")
        self.calculate_button.setEnabled(False)
        QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        try:
            result = solve(parsed, values[0], values[1], self.maximum.value())
        finally:
            self.calculate_button.setEnabled(True)
        self.current_result = result
        self.expression_label.setText(f"f(x) = {self.function.text().strip()}")
        self.derivative_label.setText(f"f′(x) = {parsed.derivative}")
        for field in (self.expression_label, self.derivative_label):
            field.setCursorPosition(0)
            field.setToolTip(field.text())
        prefix = "Raíz" if result.converged else ("Punto inicial" if result.residual is None else "Última aproximación")
        self.answer.setText(f"{prefix}: {format_number(result.root)}")
        self.status.setText(result.status.value)
        self.state_badge.setText("Convergente" if result.converged else
                                "No convergente" if result.status is Status.MAX_ITERATIONS else "Error matemático")
        final_value = None
        if result.residual is not None:
            try:
                final_value = evaluate(parsed.expression, result.root)
            except EvaluationError:
                pass
        self.function_value.setText(format_number(final_value))
        self.function_value.setToolTip("Valor con signo de f(x) en el último punto válido; el residuo es su valor absoluto.")
        self.final_error.setText(format_number(result.iterations[-1].absolute_error if result.iterations else None))
        self.iteration_count.setText(str(len(result.iterations)))
        self.details.setText(result.message)
        self.table_model.set_iterations(result.iterations)
        if result.iterations:
            self.table_stack.setCurrentWidget(self.table)
            self.table.resizeColumnsToContents()
            self.table.scrollToTop()
        else:
            self.table_empty.setText("No se necesitaron iteraciones: el punto inicial es una raíz exacta."
                                     if result.converged else "El cálculo se detuvo antes de completar la primera iteración.")
        self.plot_widget.set_result(parsed, result, values[0])
        self.current_calculation = Calculation(self.function.text().strip(), str(parsed.derivative), values[0], values[1], self.maximum.value(), result)
        for action in (self.save_action, self.pdf_action, self.csv_action):
            action.setEnabled(True)

    def load_example(self, index: int):
        if not 1 <= index <= len(EXAMPLES):
            return
        example = EXAMPLES[index - 1]
        self.function.setText(example.function)
        self.initial.setText(str(example.x0))
        self.tolerance.setText(str(example.tolerance))
        self.maximum.setValue(example.max_iterations)
        self.clear_result()
        self.example_description.setText(example.description)
        self.example_description.show()
        self.function.setFocus()

    def save_current(self):
        if self.current_calculation is None or not self.save_action.isEnabled():
            return
        try:
            self.history_service.save(self.current_calculation)
        except HistoryError as exc:
            QMessageBox.warning(self, "Historial", str(exc))
            return
        self.save_action.setEnabled(False)
        QMessageBox.information(self, "Historial", "Cálculo guardado en el historial local.")

    def show_history(self):
        self.plot_widget.stop()
        dialog = HistoryDialog(self.history_service, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_entry:
            self.restore_history(dialog.selected_entry)

    def restore_history(self, entry: HistoryEntry):
        self.reset()
        self.function.setText(entry.function)
        self.initial.setText(str(entry.x0))
        self.tolerance.setText(str(entry.tolerance))
        if not 1 <= entry.max_iterations <= 1000:
            QMessageBox.warning(self, "Historial", "El registro contiene un límite de iteraciones no válido.")
            return
        self.maximum.setValue(entry.max_iterations)
        self.calculate()
        if self.current_calculation is not None:
            self.save_action.setEnabled(False)

    def export_current(self, kind: str):
        calculation = self.current_calculation
        if calculation is None:
            return
        if kind == "csv" and not calculation.result.iterations:
            QMessageBox.warning(self, "Exportar CSV", "No hay iteraciones para exportar; no se generará un archivo vacío.")
            return
        self.plot_widget.stop()
        filename, _ = QFileDialog.getSaveFileName(self, f"Exportar {kind.upper()}", f"NewtonLab.{kind}",
                                                f"{kind.upper()} (*.{kind})", options=QFileDialog.Option.DontUseNativeDialog)
        if not filename:
            return
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(f".{kind}")
            if path.exists() and QMessageBox.question(self, "Reemplazar archivo", f"¿Reemplazar {path.name}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        try:
            if kind == "pdf":
                export_pdf(calculation, path, COLORS, self.plot_widget.current_index)
            else:
                export_csv(calculation, path)
        except ExportError as exc:
            QMessageBox.warning(self, "Exportación", str(exc))
            return
        QMessageBox.information(self, "Exportación", f"Archivo generado correctamente:\n{path}")

    def _select_iteration(self, current, _previous):
        iteration = self.table_model.iterations[current.row()] if current.isValid() else None
        self.iteration_selected.emit(iteration)
        if current.isValid() and current.row() != self.plot_widget.current_index:
            self.plot_widget.navigate(current.row())

    def _select_plot_row(self, index):
        if self.table.currentIndex().row() != index:
            self.table.selectRow(index)
            self.table.scrollTo(self.table_model.index(index, 0))

    def closeEvent(self, event):
        self.plot_widget.stop()
        self.plot_widget.resample_timer.stop()
        super().closeEvent(event)
