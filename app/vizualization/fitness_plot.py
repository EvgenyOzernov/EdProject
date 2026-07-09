import os
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QVBoxLayout, QWidget

import vizualization.ui_settings as ui

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "edproject-matplotlib"))

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class FitnessPlot(QWidget):
    """Виджет будущего графика функции качества."""

    def __init__(self) -> None:
        """Инициализация базовой разметки и холста для графика"""
        super().__init__()
        self.figure = Figure(figsize=ui.PLOT_FIGURE_SIZE)
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
        """Рисует best/average/worst fitness до выбранного поколения."""
        self.axes.clear()
        self._style_axes()
        if not snapshots or selected_index < 0:
            self.canvas.draw_idle()
            return

        visible_snapshots = snapshots[: selected_index + 1]
        generations = [
            getattr(snapshot, "generation", index)
            for index, snapshot in enumerate(visible_snapshots)
        ]
        best_values = [
            getattr(getattr(snapshot, "best_in_generation", None), "fitness", None)
            for snapshot in visible_snapshots
        ]
        average_values = [
            getattr(snapshot, "average_fitness", None)
            for snapshot in visible_snapshots
        ]
        worst_values = [
            getattr(snapshot, "worst_fitness", None)
            for snapshot in visible_snapshots
        ]

        self.axes.plot(generations, best_values, marker="o", linewidth=1.8, label="Лучшее")
        self.axes.plot(generations, average_values, marker="o", linewidth=1.8, label="Среднее")
        self.axes.plot(generations, worst_values, marker="o", linewidth=1.8, label="Худшее")
        self.axes.legend(loc="best")

        self.axes.relim()
        self.axes.autoscale_view()
        self.canvas.draw_idle()
