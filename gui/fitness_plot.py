import os
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QVBoxLayout, QWidget

import ui_settings as ui

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "edproject-matplotlib"))

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class FitnessPlot(QWidget):
    """Виджет будущего графика функции качества."""

    def __init__(self) -> None:
        """Инициализация базовой разметки и холста для графика"""
        super().__init__()
        self.figure = Figure(figsize=ui.PLOT_FIGURE_SIZE, tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(ui.PLOT_SUBPLOT_CODE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*ui.ZERO_MARGINS)
        layout.addWidget(self.canvas)
        self._style_axes()

    def _style_axes(self) -> None:
        """Настройка подписи осей и сетку."""
        self.axes.set_xlabel("Поколение")
        self.axes.set_ylabel("Fitness")
        self.axes.grid(True, alpha=ui.PLOT_GRID_ALPHA)

    def update_plot(self, snapshots: list[object], selected_index: int) -> None:
        """Очистка графика и оставление его в состоянии макета."""
        # Точки будут добавляться здесь после подключения алгоритма.
        self.axes.clear()
        self._style_axes()
        self.canvas.draw_idle()
