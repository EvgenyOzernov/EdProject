from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView, QSizePolicy

import ui_settings as ui


class GanttChartView(QGraphicsView):
    """Диаграмма Ганта для отображения расписания задач"""

    def __init__(self) -> None:
        """Инициализация объекта, масштабирование и режим перетаскивания."""
        super().__init__()
        self._scene = QGraphicsScene(self)
        self._zoom_factor = ui.GANTT_DEFAULT_ZOOM
        self._fit_to_width = True
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumHeight(ui.GANTT_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def show_schedule(self, snapshot=None) -> None:
        """Пустое состояние или переданное расписание."""
        self._scene.clear()

        # Виджет остается в пустом состоянии
        if snapshot is None or not getattr(snapshot, "schedule", None):
            self._scene.addText("Нет данных для отображения")
            self._scene.setSceneRect(*ui.GANTT_EMPTY_SCENE)
            self.fit_to_width()
            return

        # Заготовка отрисовки реального расписания.
        left_margin = ui.GANTT_LEFT_MARGIN
        top_margin = ui.GANTT_TOP_MARGIN
        row_height = ui.GANTT_ROW_HEIGHT
        bar_height = ui.GANTT_BAR_HEIGHT
        finish_max = max(item.finish for item in snapshot.schedule)
        deadline_max = max(item.task.deadline for item in snapshot.schedule)
        horizon = max(ui.GANTT_HORIZON_MIN, finish_max, deadline_max)
        width = max(ui.GANTT_MIN_WIDTH, horizon * ui.GANTT_TIME_SCALE)
        scale = width / horizon

        axis_pen = QPen(QColor(ui.COLOR_GANTT_AXIS), ui.GANTT_AXIS_WIDTH)
        text_color = QColor(ui.COLOR_GANTT_TEXT)
        axis_y = top_margin + ui.GANTT_AXIS_Y_OFFSET
        self._scene.addLine(left_margin, axis_y, left_margin + width, axis_y, axis_pen)

        tick_step = max(1, horizon // ui.GANTT_TICK_COUNT)
        for value in range(0, horizon + 1, tick_step):
            x = left_margin + value * scale
            self._scene.addLine(
                x,
                top_margin + ui.GANTT_TICK_TOP_OFFSET,
                x,
                top_margin + ui.GANTT_TICK_BOTTOM_OFFSET,
                axis_pen,
            )
            tick = self._scene.addText(str(value))
            tick.setDefaultTextColor(text_color)
            tick.setPos(x + ui.GANTT_TICK_TEXT_X_OFFSET, top_margin + ui.GANTT_TICK_TEXT_Y_OFFSET)

        for row, item in enumerate(snapshot.schedule):
            y = top_margin + row * row_height
            start_x = left_margin + item.start * scale
            width_x = max(ui.GANTT_MIN_BAR_WIDTH, item.task.duration * scale)
            deadline_x = left_margin + item.task.deadline * scale
            color = QColor(ui.COLOR_GANTT_LATE) if item.tardiness else QColor(ui.COLOR_GANTT_DONE)

            label = self._scene.addText(f"Задача {item.task.number}")
            label.setDefaultTextColor(text_color)
            label.setPos(ui.GANTT_TASK_LABEL_X, y + ui.GANTT_TASK_LABEL_Y_OFFSET)

            self._scene.addRect(
                start_x,
                y,
                width_x,
                bar_height,
                QPen(color.darker(ui.GANTT_BAR_BORDER_DARKEN)),
                QBrush(color),
            )
            inner = self._scene.addText(f"{item.task.number}: {item.start}-{item.finish}")
            inner.setDefaultTextColor(QColor(ui.COLOR_GANTT_INNER_TEXT))
            inner.setPos(start_x + ui.GANTT_BAR_TEXT_X_OFFSET, y + ui.GANTT_BAR_TEXT_Y_OFFSET)

            self._scene.addLine(
                deadline_x,
                y - ui.GANTT_DEADLINE_LINE_OFFSET,
                deadline_x,
                y + bar_height + ui.GANTT_DEADLINE_LINE_OFFSET,
                QPen(QColor(ui.COLOR_GANTT_DEADLINE_LINE), ui.GANTT_DEADLINE_LINE_WIDTH),
            )
            deadline_text = self._scene.addText(f"d={item.task.deadline}")
            deadline_text.setDefaultTextColor(QColor(ui.COLOR_GANTT_DEADLINE_TEXT))
            deadline_text.setPos(
                deadline_x + ui.GANTT_DEADLINE_TEXT_X_OFFSET,
                y + ui.GANTT_DEADLINE_TEXT_Y_OFFSET,
            )

        self._scene.setSceneRect(
            0,
            0,
            left_margin + width + ui.GANTT_EXTRA_RIGHT_SPACE,
            top_margin + len(snapshot.schedule) * row_height + ui.GANTT_SCENE_BOTTOM_PADDING,
        )
        self.fit_to_width()

    def zoom_in(self) -> None:
        """Увеличение масштаба диаграммы."""
        self._apply_zoom(ui.GANTT_ZOOM_STEP)

    def zoom_out(self) -> None:
        """Уменьшение масштаба диаграммы."""
        self._apply_zoom(1 / ui.GANTT_ZOOM_STEP)

    def fit_to_width(self) -> None:
        """Адаптирование масштаба диаграммы под ширину видимой области."""
        scene_rect = self._scene.sceneRect()
        if scene_rect.isEmpty():
            return
        self._fit_to_width = True
        self._zoom_factor = ui.GANTT_DEFAULT_ZOOM
        self.resetTransform()
        self.fitInView(scene_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _apply_zoom(self, factor: float) -> None:
        """Применяет ограниченный коэффициент масштабирования."""
        next_zoom = self._zoom_factor * factor
        if not ui.GANTT_MIN_ZOOM <= next_zoom <= ui.GANTT_MAX_ZOOM:
            return
        self._fit_to_width = False
        self._zoom_factor = next_zoom
        self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Обработка Ctrl+СКМ как масштабирование."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event) -> None:
        """Сохраняет масштаб при изменении размера."""
        super().resizeEvent(event)
        if self._fit_to_width:
            self.fit_to_width()
