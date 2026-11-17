"""Canvas persistente, geometría del historial y reproducción con Qt."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QSizePolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
import numpy as np
from app.core.plot_data import initial_interval, sample_curve, vertical_interval, tangent_points, VISUAL_LIMIT
from .theme import COLORS
from .iteration_table import format_number


class PlotWidget(QWidget):
    index_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.expression = None
        self.current_index = -1
        self._updating = False
        self._initial_view = None
        self.figure = Figure(figsize=(6, 3), facecolor=COLORS["background"])
        self.figure.subplots_adjust(left=.095, right=.98, bottom=.17, top=.89)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(130)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # La barra nativa proporciona la interacción; botones propios evitan
        # exportación, edición de subplots y textos ajenos a esta fase.
        self.toolbar = NavigationToolbar2QT(self.canvas, self, coordinates=False)
        self.toolbar.hide()
        self.timer = QTimer(self)
        self.timer.setInterval(900)
        self.timer.timeout.connect(self._tick)
        self.resample_timer = QTimer(self)
        self.resample_timer.setSingleShot(True)
        self.resample_timer.setInterval(100)
        self.resample_timer.timeout.connect(self._resample)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        tools = QHBoxLayout()
        self.home_button = self._button("Restaurar vista", self.restore_view)
        self.pan_button = self._button("Desplazar", self._pan)
        self.zoom_button = self._button("Zoom", self._zoom)
        self.pan_button.setCheckable(True)
        self.zoom_button.setCheckable(True)
        for button in (self.home_button, self.pan_button, self.zoom_button):
            tools.addWidget(button)
        tools.addStretch()
        layout.addLayout(tools)
        layout.addWidget(self.canvas, 1)
        navigation = QHBoxLayout()
        self.first_button = self._button("Primera", lambda: self.navigate(0))
        self.previous_button = self._button("Anterior", lambda: self.navigate(self.current_index - 1))
        self.next_button = self._button("Siguiente", lambda: self.navigate(self.current_index + 1))
        self.last_button = self._button("Última", lambda: self.navigate(len(self.steps) - 1))
        self.indicator = QLabel("Sin iteraciones")
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for item in (self.first_button, self.previous_button, self.indicator, self.next_button, self.last_button):
            navigation.addWidget(item)
        layout.addLayout(navigation)
        playback = QHBoxLayout()
        self.play_button = self._button("Reproducir", self.toggle_playback)
        self.restart_button = self._button("Reiniciar", self.restart)
        self.speed = QComboBox()
        self.speed.addItem("Lenta", 1600)
        self.speed.addItem("Normal", 900)
        self.speed.addItem("Rápida", 300)
        self.speed.setCurrentIndex(1)
        self.speed.setAccessibleName("Velocidad de reproducción")
        self.speed.currentIndexChanged.connect(lambda: self.timer.setInterval(self.speed.currentData()))
        playback.addWidget(self.play_button)
        playback.addWidget(self.restart_button)
        playback.addStretch()
        playback.addWidget(QLabel("Velocidad"))
        playback.addWidget(self.speed)
        layout.addLayout(playback)
        self.context = QLabel("Seleccioná una iteración para ver sus valores.")
        self.context.setObjectName("mathContext")
        self.context.setWordWrap(True)
        self.context.setTextFormat(Qt.TextFormat.PlainText)
        self.context.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.context.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.context)
        self.notice = QLabel("")
        self.notice.setObjectName("muted")
        self.notice.setWordWrap(True)
        self.notice.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.notice)
        self.clear()
        self.canvas.mpl_connect("scroll_event", self._wheel_zoom)

    @property
    def steps(self):
        return self.result.iterations if self.result else ()

    def _button(self, text, action):
        button = QPushButton(text)
        button.setObjectName("plotControl")
        button.clicked.connect(action)
        return button

    def _setup_axes(self):
        self.axes.clear()
        self.axes.set_facecolor(COLORS["background"])
        for spine in self.axes.spines.values():
            spine.set_color(COLORS["border"])
        self.axes.tick_params(colors=COLORS["secondary"], labelsize=8)
        for axis in (self.axes.xaxis, self.axes.yaxis):
            axis.get_offset_text().set_color(COLORS["secondary"])
        self.axes.set_xlabel("x", color=COLORS["secondary"], fontsize=9, labelpad=2)
        self.axes.set_ylabel("f(x)", color=COLORS["secondary"], fontsize=9, labelpad=3)
        self.axes.grid(color=COLORS["grid"], linewidth=.5)
        self.axes.axhline(0, color=COLORS["secondary"], linewidth=.7)
        self.axes.axvline(0, color=COLORS["secondary"], linewidth=.6)
        self.curve, = self.axes.plot([], [], color=COLORS["function"], linewidth=1.5, label="f(x)")
        self.tangent, = self.axes.plot([], [], color=COLORS["tangent"], linewidth=1.2, label="Tangente")
        self.approximations, = self.axes.plot([], [], "o", color=COLORS["iteration"], markersize=3, label="Iteraciones")
        self.point, = self.axes.plot([], [], "o", color=COLORS["iteration"], markersize=6)
        self.intercept, = self.axes.plot([], [], "o", color=COLORS["reference"], markersize=5)
        self.guide, = self.axes.plot([], [], "--", color=COLORS["reference"], linewidth=.8)
        self.root, = self.axes.plot([], [], "o", color=COLORS["root"], markersize=6, label="Raíz")
        self.axes.callbacks.connect("xlim_changed", self._limits_changed)

    def clear(self):
        self.stop()
        self.resample_timer.stop()
        if self.toolbar.mode.name == "PAN":
            self.toolbar.pan()
        elif self.toolbar.mode.name == "ZOOM":
            self.toolbar.zoom()
        self.pan_button.setChecked(False)
        self.zoom_button.setChecked(False)
        self.result = self.expression = None
        self.current_index = -1
        self._initial_view = None
        self._updating = True
        self._setup_axes()
        self.empty_text = self.axes.text(.5, .5, "Calculá una raíz para visualizar el método", transform=self.axes.transAxes,
                                        ha="center", va="center", color=COLORS["secondary"], fontsize=9, wrap=True)
        self._updating = False
        self.toolbar.update()
        self.context.setText("Seleccioná una iteración para ver sus valores.")
        self.notice.clear()
        self._update_controls()
        self.canvas.draw_idle()

    def set_result(self, parsed, result, x0):
        self.clear()
        self.result, self.expression = result, parsed.expression
        self.empty_text.remove()
        limits = initial_interval(x0, result)
        curve = sample_curve(self.expression, limits)
        self.curve.set_data(curve.x, curve.y)
        self.notice.setText(curve.notice)
        self._range_notice = ""
        if any(abs(x) > VISUAL_LIMIT for x in [x0, result.root] + [s.x for s in self.steps] + [s.fx for s in self.steps]):
            self._range_notice = " Algunos puntos exceden el límite visual ±1e12; consultá sus valores en la tabla."
            self.notice.setText(curve.notice + self._range_notice)
        points = [s.x for s in self.steps] + [s.next_x for s in self.steps]
        points = [x for x in points if np.isfinite(x) and abs(x) <= VISUAL_LIMIT]
        self.approximations.set_data(points, np.zeros(len(points)))
        if result.converged and abs(result.root) <= VISUAL_LIMIT:
            self.root.set_data([result.root], [0])
        self._initial_view = (limits, vertical_interval(curve.y, result))
        self.restore_view()
        handles = [self.curve]
        if self.steps:
            handles.extend([self.tangent, self.approximations])
        if result.converged:
            handles.append(self.root)
        self.axes.legend(handles=handles, loc="upper right", ncol=2, fontsize=8,
                         facecolor=COLORS["panel"], edgecolor=COLORS["border"], labelcolor=COLORS["text"])
        if self.steps:
            self.select_index(0)
        else:
            self.context.setText("Sin pasos: raíz inicial exacta." if result.converged else "No se completaron pasos; no existe una tangente válida.")
        self._update_controls()
        self.canvas.draw_idle()

    def _limits_changed(self, _axes):
        if not self._updating and self.expression is not None:
            self.resample_timer.start()

    def _resample(self):
        if self.expression is None:
            return
        limits = self.axes.get_xlim()
        if not np.isfinite(limits).all() or limits[0] >= limits[1] or max(abs(v) for v in limits) > VISUAL_LIMIT:
            self.notice.setText("La vista excede el límite visual ±1e12. Restaurá la vista inicial.")
            return
        curve = sample_curve(self.expression, limits)
        self.curve.set_data(curve.x, curve.y)
        self.notice.setText(curve.notice + self._range_notice)
        self._draw_step()
        self.canvas.draw_idle()

    def select_index(self, index):
        if not self.steps:
            return
        index = max(0, min(int(index), len(self.steps) - 1))
        changed = index != self.current_index
        self.current_index = index
        if index == len(self.steps) - 1:
            self.stop()
        self._draw_step()
        self._update_controls()
        if changed:
            self.index_changed.emit(index)
        self.canvas.draw_idle()

    def _draw_step(self):
        if not 0 <= self.current_index < len(self.steps):
            return
        step = self.steps[self.current_index]
        x, y = tangent_points(step, self.axes.get_xlim())
        self.tangent.set_data(x, y)
        valid = np.isfinite([step.x, step.fx, step.next_x, step.derivative]).all() and step.derivative != 0
        representable = valid and max(abs(step.x), abs(step.fx), abs(step.next_x)) <= VISUAL_LIMIT
        self.point.set_data([step.x] if representable else [], [step.fx] if representable else [])
        self.intercept.set_data([step.next_x] if representable else [], [0] if representable else [])
        # El punto de la siguiente curva proviene del siguiente paso almacenado.
        self.guide.set_data([], [])
        if representable and self.current_index + 1 < len(self.steps):
            next_step = self.steps[self.current_index + 1]
            if abs(next_step.fx) <= VISUAL_LIMIT:
                self.guide.set_data([step.next_x, step.next_x], [0, next_step.fx])
        f = format_number
        self.context.setText(f"n = {step.index}   ·   xₙ = {f(step.x)}   ·   f(xₙ) = {f(step.fx)}   ·   f′(xₙ) = {f(step.derivative)}\n"
                             f"xₙ₊₁ = {f(step.x)} − ({f(step.fx)}) / ({f(step.derivative)}) = {f(step.next_x)}   ·   Error = {f(step.absolute_error)}")

    def _update_controls(self):
        count = len(self.steps)
        self.indicator.setText(f"Iteración {self.current_index + 1} de {count}" if count else "Sin iteraciones")
        for button in (self.first_button, self.previous_button):
            button.setEnabled(count > 0 and self.current_index > 0)
        for button in (self.next_button, self.last_button):
            button.setEnabled(count > 0 and self.current_index < count - 1)
        self.play_button.setEnabled(count > 1)
        self.restart_button.setEnabled(count > 0)
        self.speed.setEnabled(count > 1)
        for button in (self.home_button, self.pan_button, self.zoom_button):
            button.setEnabled(self.result is not None)

    def navigate(self, index):
        self.stop()
        self.select_index(index)

    def restart(self):
        self.navigate(0)

    def stop(self):
        self.timer.stop()
        if hasattr(self, "play_button"):
            self.play_button.setText("Reproducir")

    def toggle_playback(self):
        if self.timer.isActive():
            self.stop()
        elif len(self.steps) > 1:
            if self.current_index >= len(self.steps) - 1:
                self.select_index(0)
            self.play_button.setText("Pausar")
            self.timer.start()

    def _tick(self):
        self.select_index(self.current_index + 1)

    def _pan(self):
        self.toolbar.pan()
        self.pan_button.setChecked(bool(self.toolbar.mode) and "pan" in self.toolbar.mode.name.lower())
        self.zoom_button.setChecked(False)

    def _zoom(self):
        self.toolbar.zoom()
        self.zoom_button.setChecked(bool(self.toolbar.mode) and "zoom" in self.toolbar.mode.name.lower())
        self.pan_button.setChecked(False)

    def restore_view(self):
        if self._initial_view:
            self.resample_timer.stop()
            self._updating = True
            self.axes.set_xlim(self._initial_view[0])
            self.axes.set_ylim(self._initial_view[1])
            self._updating = False
            self.toolbar.update()
            self._resample()

    def _wheel_zoom(self, event):
        if self.result is None or event.inaxes is not self.axes or event.xdata is None or event.ydata is None:
            return
        scale = .8 if event.button == "up" else 1.25
        self.axes.set_xlim([event.xdata + (v - event.xdata) * scale for v in self.axes.get_xlim()])
        self.axes.set_ylim([event.ydata + (v - event.ydata) * scale for v in self.axes.get_ylim()])
        self.canvas.draw_idle()

    def closeEvent(self, event):
        self.stop()
        self.resample_timer.stop()
        super().closeEvent(event)
