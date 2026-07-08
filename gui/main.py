import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import ui_settings as ui
from fitness_plot import FitnessPlot
from gantt_chart_view import GanttChartView


class MainWindow(QMainWindow):
    """Главное окно GUI"""

    def __init__(self) -> None:
        """Инициализирует окно, вкладки и стартовое пустое состояние"""
        super().__init__()
        self.setWindowTitle("Решение задачи минимизации суммарной задержки генетическим алгоритмом")
        self.resize(ui.WINDOW_WIDTH, ui.WINDOW_HEIGHT)
        self.setMinimumSize(ui.WINDOW_MIN_WIDTH, ui.WINDOW_MIN_HEIGHT)

        self._build_ui()
        self._connect_signals()
        self._setup_empty_task_rows()
        self._apply_styles()

    def _build_ui(self) -> None:
        """Корневуа структуру с вкладками"""
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(*ui.ROOT_MARGINS)
        root.setSpacing(ui.ROOT_SPACING)

        # Основные вкладки приложения.
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_source_data_tab(), "Источник данных")
        self.tabs.addTab(self._build_parameters_tab(), "Параметры алгоритма")
        self.tabs.addTab(self._build_run_tab(), "Запуск")
        root.addWidget(self.tabs)

    def _build_source_data_tab(self) -> QWidget:
        """Вкладка выбора источника и ввода задач"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(*ui.TAB_MARGINS)
        layout.setSpacing(ui.TAB_SPACING)
        layout.addWidget(self._build_source_group(), stretch=ui.SOURCE_GROUP_STRETCH)
        layout.addWidget(self._build_tasks_area(), stretch=ui.TASKS_GROUP_STRETCH)
        return tab

    def _build_parameters_tab(self) -> QWidget:
        """Вкладка настройки параметров алгоритма."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(*ui.TAB_MARGINS)
        layout.addWidget(self._build_algorithm_group())
        layout.addStretch(1)
        return tab

    def _build_run_tab(self) -> QWidget:
        """Вкладка запуска алгоритма и визуализации."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(*ui.TAB_MARGINS)
        layout.setSpacing(ui.TAB_SPACING)

        # Верхняя область: история поколений и диаграмма расписания.
        upper_splitter = QSplitter(Qt.Orientation.Horizontal)
        history_group = QGroupBox("История поколений")
        history_layout = QVBoxLayout(history_group)
        self.generations_list = QListWidget()
        history_layout.addWidget(self.generations_list)

        chart_group = QGroupBox("Текущее расписание")
        chart_layout = QVBoxLayout(chart_group)
        chart_toolbar = QHBoxLayout()
        chart_toolbar.addStretch(1)
        self.gantt_zoom_out_button = QPushButton("-")
        self.gantt_fit_button = QPushButton("По ширине")
        self.gantt_zoom_in_button = QPushButton("+")
        for button in (self.gantt_zoom_out_button, self.gantt_fit_button, self.gantt_zoom_in_button):
            button.setMinimumWidth(ui.GANTT_TOOL_BUTTON_MIN_WIDTH)
            chart_toolbar.addWidget(button)
        chart_layout.addLayout(chart_toolbar)
        self.gantt_view = GanttChartView()
        chart_layout.addWidget(self.gantt_view)

        upper_splitter.addWidget(history_group)
        upper_splitter.addWidget(chart_group)
        upper_splitter.setStretchFactor(0, ui.RUN_UPPER_HISTORY_STRETCH)
        upper_splitter.setStretchFactor(1, ui.RUN_UPPER_CHART_STRETCH)
        upper_splitter.setSizes(ui.RUN_UPPER_INITIAL_SIZES)

        # Нижняя область: текущие результаты алгоритма и график качества.
        lower_splitter = QSplitter(Qt.Orientation.Horizontal)
        lower_splitter.addWidget(self._build_info_group())
        lower_splitter.addWidget(self._build_plot_group())
        lower_splitter.setStretchFactor(0, ui.RUN_LOWER_INFO_STRETCH)
        lower_splitter.setStretchFactor(1, ui.RUN_LOWER_PLOT_STRETCH)
        lower_splitter.setSizes(ui.RUN_LOWER_INITIAL_SIZES)

        page_splitter = QSplitter(Qt.Orientation.Vertical)
        page_splitter.addWidget(upper_splitter)
        page_splitter.addWidget(lower_splitter)
        page_splitter.setStretchFactor(0, ui.RUN_VERTICAL_TOP_STRETCH)
        page_splitter.setStretchFactor(1, ui.RUN_VERTICAL_BOTTOM_STRETCH)

        layout.addWidget(page_splitter, stretch=1)
        layout.addWidget(self._build_control_area())
        return tab

    def _build_source_group(self) -> QGroupBox:
        """Блок выбора способа ввода данных."""
        group = QGroupBox("Источник данных")
        layout = QVBoxLayout(group)

        self.manual_radio = QRadioButton("Ввод вручную")
        self.file_radio = QRadioButton("Загрузить из файла")
        self.random_radio = QRadioButton("Случайная генерация")
        self.manual_radio.setChecked(True)

        source_buttons = QButtonGroup(self)
        source_buttons.addButton(self.manual_radio)
        source_buttons.addButton(self.file_radio)
        source_buttons.addButton(self.random_radio)

        # Переключатели меняют панель ввода.
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.manual_radio)
        radio_layout.addWidget(self.file_radio)
        radio_layout.addWidget(self.random_radio)
        layout.addLayout(radio_layout)

        self.source_stack = QStackedWidget()
        self.source_stack.addWidget(QLabel("Редактируйте задачи напрямую в таблице ниже."))
        self.source_stack.addWidget(self._build_file_source_panel())
        self.source_stack.addWidget(self._build_random_source_panel())
        layout.addWidget(self.source_stack)
        layout.addStretch(1)
        return group

    def _build_file_source_panel(self) -> QWidget:
        """Панель выбора файла"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(*ui.ZERO_MARGINS)
        self.choose_file_button = QPushButton("Выбрать файл")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Путь к файлу")
        layout.addWidget(self.choose_file_button)
        layout.addWidget(self.file_path_edit, stretch=1)
        return panel

    def _build_random_source_panel(self) -> QWidget:
        """Блок параметров случайной генерации."""
        panel = QWidget()
        layout = QFormLayout(panel)
        layout.setContentsMargins(*ui.ZERO_MARGINS)

        self.random_count_spin = QSpinBox()
        self.random_count_spin.setRange(*ui.RANDOM_TASK_COUNT_RANGE)
        self.random_count_spin.setValue(ui.RANDOM_TASK_COUNT_DEFAULT)
        self.min_duration_spin = QSpinBox()
        self.min_duration_spin.setRange(*ui.DURATION_RANGE)
        self.min_duration_spin.setValue(ui.MIN_DURATION_DEFAULT)
        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setRange(*ui.DURATION_RANGE)
        self.max_duration_spin.setValue(ui.MAX_DURATION_DEFAULT)
        self.min_deadline_spin = QSpinBox()
        self.min_deadline_spin.setRange(*ui.DEADLINE_RANGE)
        self.min_deadline_spin.setValue(ui.MIN_DEADLINE_DEFAULT)
        self.max_deadline_spin = QSpinBox()
        self.max_deadline_spin.setRange(*ui.DEADLINE_RANGE)
        self.max_deadline_spin.setValue(ui.MAX_DEADLINE_DEFAULT)
        self.generate_button = QPushButton("Сгенерировать")

        layout.addRow("Количество задач", self.random_count_spin)
        layout.addRow("Минимальное время выполнения", self.min_duration_spin)
        layout.addRow("Максимальное время выполнения", self.max_duration_spin)
        layout.addRow("Минимальный дедлайн", self.min_deadline_spin)
        layout.addRow("Максимальный дедлайн", self.max_deadline_spin)
        layout.addRow("", self.generate_button)
        return panel

    def _build_algorithm_group(self) -> QGroupBox:
        """Блок параметров генетического алгоритма."""
        group = QGroupBox("Параметры генетического алгоритма")
        outer = QHBoxLayout(group)
        left = QFormLayout()
        right = QFormLayout()

        # Левая колонка: числовые параметры запуска.
        self.population_spin = QSpinBox()
        self.population_spin.setRange(*ui.POPULATION_RANGE)
        self.population_spin.setValue(ui.POPULATION_DEFAULT)
        self.generations_spin = QSpinBox()
        self.generations_spin.setRange(*ui.GENERATIONS_RANGE)
        self.generations_spin.setValue(ui.GENERATIONS_DEFAULT)
        self.crossover_probability_spin = QDoubleSpinBox()
        self.crossover_probability_spin.setRange(*ui.PROBABILITY_RANGE)
        self.crossover_probability_spin.setSingleStep(ui.CROSSOVER_PROBABILITY_STEP)
        self.crossover_probability_spin.setValue(ui.CROSSOVER_PROBABILITY_DEFAULT)
        self.mutation_probability_spin = QDoubleSpinBox()
        self.mutation_probability_spin.setRange(*ui.PROBABILITY_RANGE)
        self.mutation_probability_spin.setSingleStep(ui.MUTATION_PROBABILITY_STEP)
        self.mutation_probability_spin.setValue(ui.MUTATION_PROBABILITY_DEFAULT)

        # Правая колонка: дополнительные настройки.
        self.selection_combo = QComboBox()
        self.selection_combo.addItem("Турнирный")
        self.crossover_combo = QComboBox()
        self.crossover_combo.addItem("OX")
        self.crossover_combo.addItem("PMX")
        self.mutation_combo = QComboBox()
        self.mutation_combo.addItem("Swap")
        self.mutation_combo.addItem("Inversion")
        for combo in (self.selection_combo, self.crossover_combo, self.mutation_combo):
            combo.setMinimumWidth(ui.COMBO_MIN_WIDTH)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.elitism_check = QCheckBox("Использовать")
        self.elitism_check.setChecked(True)
        self.elite_count_spin = QSpinBox()
        self.elite_count_spin.setRange(*ui.ELITE_COUNT_RANGE)
        self.elite_count_spin.setValue(ui.ELITE_COUNT_DEFAULT)
        self.tournament_size_spin = QSpinBox()
        self.tournament_size_spin.setRange(*ui.TOURNAMENT_SIZE_RANGE)
        self.tournament_size_spin.setValue(ui.TOURNAMENT_SIZE_DEFAULT)
        self.stagnation_limit_spin = QSpinBox()
        self.stagnation_limit_spin.setRange(*ui.STAGNATION_LIMIT_RANGE)
        self.stagnation_limit_spin.setValue(ui.STAGNATION_LIMIT_DEFAULT)
        self.stagnation_limit_spin.setSpecialValueText("Отключено")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(*ui.SEED_RANGE)
        self.seed_spin.setValue(ui.SEED_DEFAULT)

        left.addRow("Размер популяции", self.population_spin)
        left.addRow("Количество поколений", self.generations_spin)
        left.addRow("Вероятность скрещивания", self.crossover_probability_spin)
        left.addRow("Вероятность мутации", self.mutation_probability_spin)
        right.addRow("Тип отбора", self.selection_combo)
        right.addRow("Тип скрещивания", self.crossover_combo)
        right.addRow("Тип мутации", self.mutation_combo)
        right.addRow("Элитизм", self.elitism_check)
        right.addRow("Количество лучших особей", self.elite_count_spin)
        right.addRow("Размер турнира", self.tournament_size_spin)
        right.addRow("Лимит стагнации", self.stagnation_limit_spin)
        right.addRow("Seed", self.seed_spin)

        outer.addLayout(left, stretch=ui.ALGORITHM_LEFT_STRETCH)
        outer.addLayout(right, stretch=ui.ALGORITHM_RIGHT_STRETCH)
        return group

    def _build_tasks_area(self) -> QGroupBox:
        """Редактируемая таблица задач."""
        group = QGroupBox("Таблица задач")
        layout = QVBoxLayout(group)

        # Таблица редактируемая, но данные не обрабатываются
        self.tasks_table = QTableWidget(0, 3)
        self.tasks_table.setHorizontalHeaderLabels(["№", "Время выполнения", "Дедлайн"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tasks_table.verticalHeader().setVisible(False)
        self.tasks_table.setAlternatingRowColors(True)
        layout.addWidget(self.tasks_table)

        self.table_validation_label = QLabel("")
        self.table_validation_label.setStyleSheet(f"color: {ui.TABLE_ERROR_COLOR}; font-weight: 600;")
        layout.addWidget(self.table_validation_label)

        # Кнопки для управления строками таблицы
        footer = QHBoxLayout()
        self.add_task_button = QPushButton("Добавить задачу")
        self.delete_task_button = QPushButton("Удалить выбранную")
        self.clear_tasks_button = QPushButton("Очистить таблицу")
        self.total_tasks_label = QLabel("Всего задач: 0")
        self.total_tasks_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        footer.addWidget(self.add_task_button)
        footer.addWidget(self.delete_task_button)
        footer.addWidget(self.clear_tasks_button)
        footer.addStretch(1)
        footer.addWidget(self.total_tasks_label)
        layout.addLayout(footer)
        return group

    def _build_info_group(self) -> QGroupBox:
        """Блок текущих результатов выполнения алгоритма"""
        info_group = QGroupBox("Информация")
        info_layout = QFormLayout(info_group)
        self.current_generation_edit = self._readonly_line()
        self.best_fitness_edit = self._readonly_line()
        self.average_fitness_edit = self._readonly_line()
        self.worst_fitness_edit = self._readonly_line()
        self.total_tardiness_edit = self._readonly_line()
        self.best_schedule_edit = self._readonly_line()
        info_layout.addRow("Текущее поколение", self.current_generation_edit)
        info_layout.addRow("Лучшее значение Fitness", self.best_fitness_edit)
        info_layout.addRow("Среднее Fitness", self.average_fitness_edit)
        info_layout.addRow("Худшее Fitness", self.worst_fitness_edit)
        info_layout.addRow("Суммарная задержка", self.total_tardiness_edit)
        info_layout.addRow("Лучшее расписание", self.best_schedule_edit)
        return info_group

    def _build_plot_group(self) -> QGroupBox:
        """Блок графика функции качества."""
        plot_group = QGroupBox("График функции качества")
        plot_layout = QVBoxLayout(plot_group)
        self.fitness_plot = FitnessPlot()
        plot_layout.addWidget(self.fitness_plot)
        return plot_group

    def _build_control_area(self) -> QWidget:
        """Панель кнопок управления работой алгоритма"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_button = QPushButton("Старт")
        self.pause_button = QPushButton("Пауза")
        self.next_button = QPushButton("Следующий шаг")
        self.previous_button = QPushButton("Предыдущий шаг")
        self.finish_button = QPushButton("До конца")
        self.reset_button = QPushButton("Сброс")

        for button in (
            self.start_button,
            self.pause_button,
            self.next_button,
            self.previous_button,
            self.finish_button,
            self.reset_button,
        ):
            button.setMinimumWidth(ui.CONTROL_BUTTON_MIN_WIDTH)
            layout.addWidget(button)

        return panel

    def _readonly_line(self) -> QLineEdit:
        """Возвращает поле только для отображения будущей статистики."""
        line = QLineEdit()
        line.setReadOnly(True)
        return line

    def _connect_signals(self) -> None:
        """Подключение обработчиков сигналов кнопок и переключателей"""
        self.manual_radio.toggled.connect(self._update_source_panel)
        self.file_radio.toggled.connect(self._update_source_panel)
        self.random_radio.toggled.connect(self._update_source_panel)
        self.choose_file_button.clicked.connect(self.noop)
        self.generate_button.clicked.connect(self.noop)
        self.elitism_check.toggled.connect(self._sync_elitism_controls)
        self.add_task_button.clicked.connect(self.noop)
        self.delete_task_button.clicked.connect(self.noop)
        self.clear_tasks_button.clicked.connect(self.noop)
        self.generations_list.currentRowChanged.connect(self.noop)
        self.gantt_zoom_out_button.clicked.connect(self.noop)
        self.gantt_fit_button.clicked.connect(self.noop)
        self.gantt_zoom_in_button.clicked.connect(self.noop)
        self.start_button.clicked.connect(self.noop)
        self.pause_button.clicked.connect(self.noop)
        self.next_button.clicked.connect(self.noop)
        self.previous_button.clicked.connect(self.noop)
        self.finish_button.clicked.connect(self.noop)
        self.reset_button.clicked.connect(self.noop)
        self._sync_elitism_controls()

    def _apply_styles(self) -> None:
        """Применяет общий стиль виджетов приложения."""
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{
                background: {ui.COLOR_BACKGROUND};
                color: {ui.COLOR_TEXT};
                font-size: {ui.BASE_FONT_SIZE}px;
            }}
            QGroupBox {{
                background: {ui.COLOR_GROUP_BACKGROUND};
                border: 1px solid {ui.COLOR_GROUP_BORDER};
                border-radius: {ui.GROUP_BORDER_RADIUS}px;
                margin-top: {ui.GROUP_MARGIN_TOP}px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {ui.GROUP_TITLE_LEFT_PADDING}px;
                padding: {ui.GROUP_TITLE_PADDING};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTableWidget, QListWidget {{
                background: {ui.COLOR_GROUP_BACKGROUND};
                border: 1px solid {ui.COLOR_INPUT_BORDER};
                border-radius: {ui.INPUT_BORDER_RADIUS}px;
                padding: {ui.CONTROL_PADDING};
                font-weight: 400;
            }}
            QPushButton {{
                background: {ui.COLOR_BUTTON};
                border: 1px solid {ui.COLOR_BUTTON_BORDER};
                border-radius: {ui.BUTTON_BORDER_RADIUS}px;
                color: {ui.COLOR_GANTT_INNER_TEXT};
                padding: {ui.BUTTON_PADDING};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {ui.COLOR_BUTTON_HOVER};
            }}
            QPushButton:disabled {{
                background: {ui.COLOR_BUTTON_DISABLED};
                border-color: {ui.COLOR_BUTTON_DISABLED};
            }}
            QHeaderView::section {{
                background: {ui.COLOR_HEADER_BACKGROUND};
                border: 1px solid {ui.COLOR_GROUP_BORDER};
                padding: {ui.HEADER_PADDING};
                font-weight: 600;
            }}
            """
        )

    def _update_source_panel(self) -> None:
        """Переключает видимую панель источника данных."""
        if self.file_radio.isChecked():
            self.source_stack.setCurrentIndex(1)
        elif self.random_radio.isChecked():
            self.source_stack.setCurrentIndex(2)
        else:
            self.source_stack.setCurrentIndex(0)

    def _sync_elitism_controls(self) -> None:
        """Включает или отключает поле количества лучших видов"""
        enabled = self.elitism_check.isChecked()
        self.elite_count_spin.setEnabled(enabled)
        if enabled and self.elite_count_spin.value() == 0:
            self.elite_count_spin.setValue(1)

    def _setup_empty_task_rows(self) -> None:
        """Заполняет таблицу пустыми строками для ручного ввода."""
        self.tasks_table.setRowCount(ui.TASK_TABLE_INITIAL_ROWS)

        # Первая колонка для визуальной нумерации строк.
        for row in range(self.tasks_table.rowCount()):
            number_item = QTableWidgetItem(str(row + 1))
            number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_table.setItem(row, 0, number_item)

            duration_item = QTableWidgetItem("")
            deadline_item = QTableWidgetItem("")
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            deadline_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_table.setItem(row, 1, duration_item)
            self.tasks_table.setItem(row, 2, deadline_item)

        self.total_tasks_label.setText(f"Всего задач: {self.tasks_table.rowCount()}")
        self.table_validation_label.setText("")
        self.gantt_view.show_schedule()
        self.fitness_plot.update_plot([], -1)

    def noop(self, *args, **kwargs) -> None:
        """Пустой обработчик для кнопок макета"""
        return None


def main() -> int:
    """Запуск приложения"""
    app = QApplication(sys.argv)
    app.setApplicationName("GA Scheduling GUI")
    font = QFont()
    font.setPointSize(ui.APP_FONT_POINT_SIZE)
    app.setFont(font)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())