import pytest
from PySide6.QtCore import QModelIndex, Qt
from app.core.models import Iteration
from app.ui.iteration_table import IterationTableModel, format_number


@pytest.mark.parametrize("value, expected", [
    (None, "—"), (0.0, "0"), (-0.0, "0"), (1.234567890123456, "1.23456789012"),
    (1e-20, "1e-20"), (1e20, "1e+20"), (-2.75, "-2.75"),
])
def test_compact_number_format(value, expected):
    assert format_number(value) == expected


def test_model_reads_original_data_without_losing_precision():
    model = IterationTableModel()
    assert model.rowCount() == 0
    assert model.columnCount() == 6
    step = Iteration(7, 1.234567890123456, -0.2, 3.0, 1.3, 0.07, 0.01)
    model.set_iterations((step,))
    assert model.iterations[0] is step
    for column, value in enumerate((7, step.x, -0.2, 3.0, 1.3, 0.07)):
        index = model.index(0, column)
        assert model.data(index, Qt.ItemDataRole.UserRole) == value
        assert model.data(index, Qt.ItemDataRole.TextAlignmentRole) & Qt.AlignmentFlag.AlignRight
        assert not model.flags(index) & Qt.ItemFlag.ItemIsEditable
    assert model.data(model.index(0, 1)) == "1.23456789012"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.ToolTipRole) == repr(step.x)
    assert model.data(QModelIndex()) is None
    assert model.headerData(0, Qt.Orientation.Horizontal) == "n"
    assert model.rowCount(model.index(0, 0)) == 0
    model.set_iterations(())
    assert model.rowCount() == 0
