from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QAbstractItemView, QHeaderView, QMessageBox
from app.services.history_service import HistoryService, HistoryEntry, HistoryError


class HistoryDialog(QDialog):
    def __init__(self, service: HistoryService, parent=None):
        super().__init__(parent)
        self.service = service
        self.selected_entry: HistoryEntry | None = None
        self.entries: list[HistoryEntry] = []
        self.setWindowTitle("Historial de cálculos")
        self.resize(850, 440)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar por función…")
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Fecha", "Función", "x inicial", "Raíz", "Estado"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)
        actions = QHBoxLayout()
        self.open_button = QPushButton("Abrir cálculo")
        self.delete_button = QPushButton("Eliminar")
        self.clear_button = QPushButton("Vaciar historial")
        close = QPushButton("Cerrar")
        for button in (self.open_button, self.delete_button, self.clear_button, close):
            actions.addWidget(button)
        layout.addLayout(actions)
        self.open_button.clicked.connect(self.open_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.clear_button.clicked.connect(self.clear_history)
        close.clicked.connect(self.reject)
        self.table.cellDoubleClicked.connect(lambda *_: self.open_selected())
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(150)
        self.search_timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        self.refresh()

    def refresh(self):
        try:
            self.entries = self.service.recent(self.search.text())
        except HistoryError as exc:
            self.entries = []
            self.feedback.setText(str(exc))
        else:
            self.feedback.setText(f"{len(self.entries)} cálculos. Al abrir, se recalcula con el motor actual sin guardar duplicados." if self.entries else "No hay cálculos que mostrar.")
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            try:
                date = datetime.fromisoformat(entry.created_at).astimezone().strftime("%d/%m/%Y %H:%M")
            except ValueError:
                date = entry.created_at
            values = (date, entry.function, f"{entry.x0:.12g}", "No confirmada" if entry.root is None else f"{entry.root:.12g}", entry.status)
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self.table.setItem(row, column, item)
        self._selection_changed()

    def _selection_changed(self):
        selected = 0 <= self.table.currentRow() < len(self.entries)
        self.open_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    def open_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.entries):
            self.selected_entry = self.entries[row]
            self.accept()

    def delete_selected(self):
        row = self.table.currentRow()
        if not 0 <= row < len(self.entries):
            return
        if QMessageBox.question(self, "Eliminar cálculo", "¿Eliminar el cálculo seleccionado?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete(self.entries[row].id)
        except HistoryError as exc:
            self.feedback.setText(str(exc))
            return
        self.refresh()

    def clear_history(self):
        if QMessageBox.question(self, "Vaciar historial", "¿Eliminar todos los cálculos guardados? Esta acción no se puede deshacer.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.clear()
        except HistoryError as exc:
            self.feedback.setText(str(exc))
            return
        self.refresh()
