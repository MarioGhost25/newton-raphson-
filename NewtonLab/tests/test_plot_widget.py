import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.ui.main_window import MainWindow


@pytest.fixture
def window():
    application = QApplication.instance() or QApplication([])
    instance = MainWindow()
    instance.show()
    instance.calculate()
    application.processEvents()
    yield instance
    instance.close()
    application.processEvents()


def test_table_and_plot_navigation_stay_in_sync(window):
    plot = window.plot_widget
    assert plot.current_index == window.table.currentIndex().row() == 0
    selected = []
    plot.index_changed.connect(selected.append)
    plot.next_button.click()
    assert plot.current_index == window.table.currentIndex().row() == 1
    assert selected == [1]
    window.table.selectRow(2)
    assert plot.current_index == 2
    assert selected == [1, 2]
    plot.last_button.click()
    assert plot.current_index == len(plot.steps) - 1
    QApplication.processEvents()
    assert window.table.viewport().rect().contains(window.table.visualRect(window.table.currentIndex()).center())
    center = window.table.visualRect(window.table.currentIndex()).center()
    assert window.analysis_panel.rect().contains(window.table.viewport().mapTo(window.analysis_panel, center))
    assert not plot.next_button.isEnabled()
    plot.navigate(10000)
    assert plot.current_index == len(plot.steps) - 1
    plot.first_button.click()
    plot.navigate(-10000)
    assert plot.current_index == 0
    assert not plot.previous_button.isEnabled()
    assert not plot.first_button.isEnabled()


def test_artists_use_engine_values_and_canvas_is_reused(window):
    plot = window.plot_widget
    canvas, figure = plot.canvas, plot.figure
    plot.navigate(1)
    step = window.current_result.iterations[1]
    assert plot.point.get_xdata()[0] == step.x
    assert plot.point.get_ydata()[0] == step.fx
    assert plot.intercept.get_xdata()[0] == step.next_x
    assert plot.intercept.get_ydata()[0] == 0
    assert "n = 2" in plot.context.text()
    assert plot.root.get_xdata()[0] == window.current_result.root
    window.calculate()
    assert plot.canvas is canvas and plot.figure is figure


def test_timer_play_pause_restart_and_automatic_finish(window):
    plot = window.plot_widget
    plot.play_button.click()
    assert plot.timer.isActive()
    assert plot.play_button.text() == "Pausar"
    plot.play_button.click()
    assert not plot.timer.isActive()
    plot.last_button.click()
    plot.play_button.click()
    assert plot.current_index == 0
    plot.timer.setInterval(1)
    for _ in range(30):
        QTest.qWait(10)
        if not plot.timer.isActive():
            break
    assert plot.current_index == len(plot.steps) - 1
    assert not plot.timer.isActive()
    assert window.table.currentIndex().row() == plot.current_index
    plot.restart_button.click()
    assert plot.current_index == 0
    assert not plot.timer.isActive()
    plot.speed.setCurrentIndex(2)
    assert plot.timer.interval() == 300


@pytest.mark.parametrize("action", ["clear", "new", "edit", "close"])
def test_playback_stops_on_lifecycle_events(window, action):
    plot = window.plot_widget
    plot.play_button.click()
    if action == "clear":
        window.reset()
        assert plot.result is None and plot.current_index == -1
        assert len(plot.curve.get_xdata()) == 0
        assert not plot.play_button.isEnabled()
    elif action == "new":
        window.calculate()
        assert plot.current_index == 0
    elif action == "edit":
        window.function.setText("x +")
        window.calculate()
        assert plot.result is None
    else:
        window.close()
    assert not plot.timer.isActive()
    assert not plot.resample_timer.isActive()


def test_nonconvergence_keeps_steps_without_root_marker(window):
    window.function.setText("x**3-2*x+2")
    window.initial.setText("0")
    window.maximum.setValue(8)
    window.calculate()
    plot = window.plot_widget
    assert len(plot.steps) == 8
    assert len(plot.root.get_xdata()) == 0
    plot.navigate(7)
    assert plot.current_index == 7
    window.resize(1600, 1000)
    QApplication.processEvents()
    window.resize(900, 700)
    QApplication.processEvents()
    current_rect = window.table.visualRect(window.table.currentIndex())
    assert window.table.viewport().rect().contains(current_rect.center())


def test_domain_failure_and_exact_root_have_no_tangent(window):
    window.function.setText("log(x)")
    window.initial.setText("-1")
    window.calculate()
    plot = window.plot_widget
    assert not np.isfinite(plot.curve.get_ydata()).any()
    assert plot.notice.text()
    assert len(plot.tangent.get_xdata()) == 0
    assert not plot.next_button.isEnabled()
    window.function.setText("x**2")
    window.initial.setText("0")
    window.calculate()
    assert len(plot.tangent.get_xdata()) == 0
    assert plot.root.get_xdata()[0] == 0
    assert not plot.play_button.isEnabled()


def test_zoom_pan_restore_and_resampling(window):
    plot = window.plot_widget
    initial = plot.axes.get_xlim()
    plot.pan_button.click()
    assert plot.toolbar.mode.name == "PAN"
    plot.zoom_button.click()
    assert plot.toolbar.mode.name == "ZOOM"
    assert not plot.pan_button.isChecked()
    plot.axes.set_xlim(3, 5)
    plot._resample()
    assert plot.curve.get_xdata()[0] == 3
    assert plot.curve.get_xdata()[-1] == 5
    plot.home_button.click()
    assert plot.axes.get_xlim() == initial
    window.reset()
    assert plot.toolbar.mode.name == "NONE"
    assert not plot.pan_button.isChecked()
    assert not plot.zoom_button.isChecked()
