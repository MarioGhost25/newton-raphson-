"""Presentación del historial del motor, sin cálculos numéricos nuevos."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView, QTableView
from app.core.models import Iteration


def format_number(value: float | None) -> str:
    if value is None:
        return "—"
    return "0" if value == 0 else f"{value:.12g}"


class IterationTableModel(QAbstractTableModel):
    HEADERS = ("n", "xₙ", "f(xₙ)", "f′(xₙ)", "xₙ₊₁", "Error absoluto")
    FIELDS = ("index", "x", "fx", "derivative", "next_x", "absolute_error")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.iterations: tuple[Iteration, ...] = ()

    def set_iterations(self, iterations: tuple[Iteration, ...]):
        self.beginResetModel()
        self.iterations = tuple(iterations)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.iterations)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() and 0 <= index.column() < self.columnCount()):
            return None
        value = getattr(self.iterations[index.row()], self.FIELDS[index.column()])
        if role == Qt.ItemDataRole.DisplayRole:
            return str(value) if index.column() == 0 else format_number(value)
        if role == Qt.ItemDataRole.ToolTipRole:
            return str(value) if index.column() == 0 else repr(value)
        if role == Qt.ItemDataRole.UserRole:
            return value
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None


class IterationTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(27)
        self.horizontalHeader().setMinimumSectionSize(44)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setAccessibleName("Tabla de iteraciones de Newton-Raphson")
        self.copy_action = QAction("Copiar selección", self)
        self.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        self.copy_action.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        self.copy_action.triggered.connect(self.copy_selection)
        self.addAction(self.copy_action)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

    def copy_selection(self):
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return
        # Copia la precisión almacenada; el formato compacto es solo visual.
        rows = sorted({index.row() for index in indexes})
        columns = sorted({index.column() for index in indexes})
        selected = {(index.row(), index.column()) for index in indexes}
        model = self.model()
        lines = ["\t".join(str(model.data(model.index(row, column), Qt.ItemDataRole.UserRole))
                           if (row, column) in selected else "" for column in columns) for row in rows]
        QApplication.clipboard().setText("\n".join(lines))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.currentIndex().isValid():
            self.scrollTo(self.currentIndex())
