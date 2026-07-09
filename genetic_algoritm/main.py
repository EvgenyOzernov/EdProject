import csv
import random
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
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
    QFileDialog,
    QMessageBox,
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

ALGORITHM_DIR = Path(__file__).resolve().parents[1] / "genetic_algoritm"
if str(ALGORITHM_DIR) not in sys.path:
    sys.path.insert(0, str(ALGORITHM_DIR))

from genetic_scheduler import GAConfig, RunResult, SolutionSnapshot, Task, run_all

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
        """Корневая структура с вкладками."""
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

        # Верхняя область: список особей текущего поколения и диаграмма расписания.
        upper_splitter = QSplitter(Qt.Orientation.Horizontal)
        individuals_group = QGroupBox("Особи текущего поколения")
        individuals_layout = QVBoxLayout(individuals_group)
        self.individuals_list = QListWidget()
        individuals_layout.addWidget(self.individuals_list)

        chart_group = QGroupBox("Расписание выбранной особи")
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

        upper_splitter.addWidget(individuals_group)
        upper_splitter.addWidget(chart_group)
        upper_splitter.setStretchFactor(0, ui.RUN_UPPER_INDIVIDUALS_STRETCH)
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
        self.reload_file_button = QPushButton("Обновить")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Путь к файлу")
        layout.addWidget(self.choose_file_button)
        layout.addWidget(self.reload_file_button)
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
        self.selection_combo.addItem("Турнирный", "tournament")
        self.crossover_combo = QComboBox()
        self.crossover_combo.addItem("OX", "order_crossover")
        self.crossover_combo.addItem("PMX", "pmx")
        self.mutation_combo = QComboBox()
        self.mutation_combo.addItem("Swap", "swap")
        self.mutation_combo.addItem("Inversion", "inversion")
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

        # Таблица для ручного ввода задач алгоритма.
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
        self.choose_file_button.clicked.connect(self._choose_tasks_file)
        self.reload_file_button.clicked.connect(self._reload_selected_tasks_file)
        self.generate_button.clicked.connect(self._generate_random_tasks)
        self.elitism_check.toggled.connect(self._sync_elitism_controls)
        self.add_task_button.clicked.connect(self._add_task_row)
        self.delete_task_button.clicked.connect(self._delete_selected_task_rows)
        self.clear_tasks_button.clicked.connect(self._clear_tasks_table)
        self.individuals_list.currentRowChanged.connect(self.noop)
        self.gantt_zoom_out_button.clicked.connect(self.noop)
        self.gantt_fit_button.clicked.connect(self.noop)
        self.gantt_zoom_in_button.clicked.connect(self.noop)
        self.start_button.clicked.connect(self._run_algorithm)
        self.pause_button.clicked.connect(self.noop)
        self.next_button.clicked.connect(self.noop)
        self.previous_button.clicked.connect(self.noop)
        self.finish_button.clicked.connect(self.noop)
        self.reset_button.clicked.connect(self._reset_run_output)
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
        """Включает или отключает поле количества элитных особей."""
        enabled = self.elitism_check.isChecked()
        self.elite_count_spin.setEnabled(enabled)
        if enabled and self.elite_count_spin.value() == 0:
            self.elite_count_spin.setValue(1)

    def _setup_empty_task_rows(self) -> None:
        """Заполняет таблицу пустыми строками для ручного ввода."""
        self.tasks_table.setRowCount(ui.TASK_TABLE_INITIAL_ROWS)

        for row in range(self.tasks_table.rowCount()):
            self._prepare_task_row(row)

        self._update_task_numbers()
        self.table_validation_label.setText("")
        self.gantt_view.show_schedule()
        self.fitness_plot.update_plot([], -1)

    def _prepare_task_row(self, row: int, duration: str = "", deadline: str = "") -> None:
        """Создает ячейки одной строки таблицы задач."""
        number_item = QTableWidgetItem(str(row + 1))
        number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tasks_table.setItem(row, 0, number_item)

        for column, value in ((1, duration), (2, deadline)):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_table.setItem(row, column, item)

    def _add_task_row(self) -> None:
        """Добавляет пустую строку для новой задачи."""
        row = self.tasks_table.rowCount()
        self.tasks_table.insertRow(row)
        self._prepare_task_row(row)
        self._update_task_numbers()
        self.table_validation_label.setText("")

    def _delete_selected_task_rows(self) -> None:
        """Удаляет выбранные строки таблицы задач."""
        selected_rows = sorted(
            {index.row() for index in self.tasks_table.selectedIndexes()},
            reverse=True,
        )
        if not selected_rows:
            return

        for row in selected_rows:
            self.tasks_table.removeRow(row)
        self._update_task_numbers()
        self.table_validation_label.setText("")

    def _clear_tasks_table(self) -> None:
        """Очищает таблицу и оставляет стартовый набор пустых строк."""
        self.tasks_table.setRowCount(0)
        self._setup_empty_task_rows()
        self._reset_run_output()

    def _choose_tasks_file(self) -> None:
        """Выбирает файл с задачами и загружает данные в таблицу."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с задачами",
            "",
            "Текстовые файлы (*.txt *.csv);;Все файлы (*)",
        )
        if not file_path:
            return

        self._load_tasks_file(Path(file_path))

    def _reload_selected_tasks_file(self) -> None:
        """Повторно читает файл, путь к которому уже выбран в поле."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            self._show_validation_error("Сначала выберите файл с задачами.")
            return

        self._load_tasks_file(Path(file_path))

    def _load_tasks_file(self, path: Path) -> None:
        """Проверяет файл по текущему содержимому и переносит задачи в таблицу."""
        self.table_validation_label.setText("")
        self._clear_table_error_marks()

        try:
            rows = self._read_task_rows_from_file(path)
        except ValueError as error:
            self._show_validation_error(str(error))
            return
        except OSError as error:
            self._show_validation_error(f"Не удалось прочитать файл: {error}")
            return

        self.file_path_edit.setText(str(path))
        self._fill_tasks_table(rows)
        self.table_validation_label.setText(f"Загружено задач: {len(rows)}")

    def _generate_random_tasks(self) -> None:
        """Заполняет таблицу случайно сгенерированными задачами."""
        min_duration = self.min_duration_spin.value()
        max_duration = self.max_duration_spin.value()
        min_deadline = self.min_deadline_spin.value()
        max_deadline = self.max_deadline_spin.value()
        if min_duration > max_duration or min_deadline > max_deadline:
            self._show_validation_error(
                "Минимальные значения генерации не должны быть больше максимальных."
            )
            return

        generator = random.Random(self.seed_spin.value())
        rows = [
            (
                generator.randint(min_duration, max_duration),
                generator.randint(min_deadline, max_deadline),
            )
            for _ in range(self.random_count_spin.value())
        ]
        self._fill_tasks_table(rows)
        self.table_validation_label.setText(f"Сгенерировано задач: {len(rows)}")

    def _read_task_rows_from_file(self, path: Path) -> list[tuple[int, int]]:
        """Читает пары duration/deadline из CSV или текстового файла."""
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError("Файл пустой.")

        sample = content[:1024]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t ")
            raw_rows = csv.reader(content.splitlines(), dialect)
        except csv.Error:
            raw_rows = (line.split() for line in content.splitlines())

        parsed_rows: list[tuple[int, int]] = []
        for line_number, row in enumerate(raw_rows, start=1):
            values = [value.strip() for value in row if value.strip()]
            if not values:
                continue

            duration, deadline = self._parse_file_row(values)
            if duration is None or deadline is None:
                if line_number == 1:
                    continue
                raise ValueError(
                    f"Некорректная строка {line_number}. "
                    "Ожидается: duration, deadline или id, duration, deadline."
                )
            parsed_rows.append((duration, deadline))

        if not parsed_rows:
            raise ValueError("В файле не найдено ни одной корректной задачи.")
        return parsed_rows

    def _parse_file_row(self, values: list[str]) -> tuple[int | None, int | None]:
        """Преобразует строку файла в пару duration/deadline."""
        if len(values) >= 3:
            duration_text, deadline_text = values[1], values[2]
        elif len(values) >= 2:
            duration_text, deadline_text = values[0], values[1]
        else:
            return None, None
        return self._parse_positive_int(duration_text), self._parse_non_negative_int(deadline_text)

    def _fill_tasks_table(self, rows: list[tuple[int, int]]) -> None:
        """Переносит подготовленные пары duration/deadline в таблицу."""
        self.tasks_table.setRowCount(0)
        for row, (duration, deadline) in enumerate(rows):
            self.tasks_table.insertRow(row)
            self._prepare_task_row(row, str(duration), str(deadline))
        self._update_task_numbers()
        self._reset_run_output()

    def _update_task_numbers(self) -> None:
        """Обновляет визуальные номера строк и счетчик задач."""
        for row in range(self.tasks_table.rowCount()):
            item = self.tasks_table.item(row, 0)
            if item is None:
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tasks_table.setItem(row, 0, item)
            item.setText(str(row + 1))
        self.total_tasks_label.setText(f"Всего задач: {self.tasks_table.rowCount()}")

    def _run_algorithm(self) -> None:
        """Запускает полный расчет алгоритма и показывает текстовый результат."""
        try:
            tasks = self._collect_tasks()
            config = self._build_config()
            result = run_all(tasks, config)
        except ValueError as error:
            self._show_validation_error(str(error))
            return
        except Exception as error:
            QMessageBox.critical(self, "Ошибка запуска", f"Алгоритм завершился с ошибкой:\n{error}")
            return

        self._show_run_result(result)

    def _collect_tasks(self) -> list[Task]:
        """Читает валидные задачи из таблицы для передачи в алгоритм."""
        tasks: list[Task] = []
        invalid_cells: list[tuple[int, int]] = []
        self._clear_table_error_marks()

        for row in range(self.tasks_table.rowCount()):
            duration_text = self._cell_text(row, 1)
            deadline_text = self._cell_text(row, 2)
            if not duration_text and not deadline_text:
                continue

            duration = self._parse_positive_int(duration_text)
            deadline = self._parse_non_negative_int(deadline_text)
            if duration is None:
                invalid_cells.append((row, 1))
            if deadline is None:
                invalid_cells.append((row, 2))
            if duration is not None and deadline is not None:
                tasks.append(Task(id=row + 1, duration=duration, deadline=deadline))

        if invalid_cells:
            self._mark_invalid_cells(invalid_cells)
            raise ValueError(
                "Проверьте таблицу задач: время должно быть положительным целым числом, "
                "дедлайн - неотрицательным целым числом."
            )
        if not tasks:
            raise ValueError("Добавьте хотя бы одну задачу с временем выполнения и дедлайном.")
        return tasks

    def _build_config(self) -> GAConfig:
        """Собирает параметры алгоритма из элементов управления."""
        stagnation_limit = self.stagnation_limit_spin.value() or None
        return GAConfig(
            population_size=self.population_spin.value(),
            generations=self.generations_spin.value(),
            mutation_rate=self.mutation_probability_spin.value(),
            crossover_rate=self.crossover_probability_spin.value(),
            elite_count=(
                self.elite_count_spin.value() if self.elitism_check.isChecked() else 0
            ),
            tournament_size=self.tournament_size_spin.value(),
            selection_method=self.selection_combo.currentData(),
            crossover_method=self.crossover_combo.currentData(),
            mutation_method=self.mutation_combo.currentData(),
            random_seed=self.seed_spin.value(),
            stagnation_limit=stagnation_limit,
            history_enabled=True,
        )

    def _show_run_result(self, result: RunResult) -> None:
        """Выводит итог алгоритма без графика и диаграммы."""
        final_state = result.history[-1] if result.history else None
        best = result.best_solution

        self.current_generation_edit.setText(str(final_state.generation if final_state else ""))
        self.best_fitness_edit.setText(str(best.fitness))
        self.average_fitness_edit.setText(
            f"{final_state.average_fitness:.2f}" if final_state else ""
        )
        self.worst_fitness_edit.setText(str(final_state.worst_fitness if final_state else ""))
        self.total_tardiness_edit.setText(str(best.total_tardiness))
        self.best_schedule_edit.setText(self._format_task_order(best))
        self.table_validation_label.setText(
            f"Расчет завершен: {self._stop_reason_text(result.stop_reason)}"
        )
        self._fill_individuals_list(final_state.population if final_state else ())
        self.tabs.setCurrentIndex(2)

    def _fill_individuals_list(self, population: tuple[SolutionSnapshot, ...]) -> None:
        """Показывает особей последнего поколения текстовым списком."""
        self.individuals_list.clear()
        for index, snapshot in enumerate(population, start=1):
            self.individuals_list.addItem(
                f"Особь {index}: fitness={snapshot.fitness}, порядок={self._format_task_order(snapshot)}"
            )

    def _reset_run_output(self) -> None:
        """Очищает поля результата запуска."""
        self.current_generation_edit.clear()
        self.best_fitness_edit.clear()
        self.average_fitness_edit.clear()
        self.worst_fitness_edit.clear()
        self.total_tardiness_edit.clear()
        self.best_schedule_edit.clear()
        self.individuals_list.clear()
        self.table_validation_label.setText("")

    def _show_validation_error(self, message: str) -> None:
        """Показывает ошибку ввода без падения приложения."""
        self.table_validation_label.setText(message)
        QMessageBox.warning(self, "Некорректные данные", message)

    def _clear_table_error_marks(self) -> None:
        """Снимает подсветку ошибок с редактируемых ячеек."""
        for row in range(self.tasks_table.rowCount()):
            for column in (1, 2):
                item = self.tasks_table.item(row, column)
                if item is not None:
                    item.setBackground(QColor(ui.COLOR_GROUP_BACKGROUND))

    def _mark_invalid_cells(self, cells: list[tuple[int, int]]) -> None:
        """Подсвечивает ячейки с некорректными значениями."""
        for row, column in cells:
            item = self.tasks_table.item(row, column)
            if item is not None:
                item.setBackground(QColor(ui.TABLE_ERROR_COLOR))

    def _cell_text(self, row: int, column: int) -> str:
        """Возвращает очищенный текст из ячейки таблицы."""
        item = self.tasks_table.item(row, column)
        return item.text().strip() if item is not None else ""

    @staticmethod
    def _parse_positive_int(value: str) -> int | None:
        """Преобразует строку в положительное целое число."""
        try:
            number = int(value)
        except ValueError:
            return None
        return number if number > 0 else None

    @staticmethod
    def _parse_non_negative_int(value: str) -> int | None:
        """Преобразует строку в неотрицательное целое число."""
        try:
            number = int(value)
        except ValueError:
            return None
        return number if number >= 0 else None

    @staticmethod
    def _format_task_order(snapshot: SolutionSnapshot) -> str:
        """Форматирует порядок задач для текстового поля."""
        return " -> ".join(str(task_id) for task_id in snapshot.task_order)

    @staticmethod
    def _stop_reason_text(reason: str) -> str:
        """Возвращает понятное описание причины завершения."""
        reasons = {
            "completed_generations": "выполнено заданное число поколений",
            "stagnation_limit_reached": "достигнут лимит стагнации",
        }
        return reasons.get(reason, reason)

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
