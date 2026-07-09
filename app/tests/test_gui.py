import sys
import os
import pytest
from PyQt6.QtCore import Qt

# Добавляем текущую директорию в путь, чтобы pytest видел main.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import MainWindow
import vizualization.ui_settings as ui

@pytest.fixture
def app(qtbot):
    """Инициализация главного окна"""
    test_app = MainWindow()
    qtbot.addWidget(test_app)
    return test_app

def test_initial_state(app):
    """Проверка начального состояния приложения"""
    assert app.windowTitle().startswith("Решение задачи")
    assert app.tasks_table.rowCount() == ui.TASK_TABLE_INITIAL_ROWS
    assert app.start_button.isEnabled()

def test_validation_logic(app, qtbot):
    """Проверка активации кнопки при вводе данных"""
    # Изначально кнопка выключена
    # Вводим корректные данные в первую строку
    app.tasks_table.item(0, 1).setText("10")
    app.tasks_table.item(0, 2).setText("20")
    
    qtbot.wait(100) # Ждем обработки сигнала itemChanged
    assert app.start_button.isEnabled()

def test_add_delete_task(app, qtbot):
    """Тест добавления и удаления строк в таблице"""
    initial_rows = app.tasks_table.rowCount()
    qtbot.mouseClick(app.add_task_button, Qt.MouseButton.LeftButton)
    assert app.tasks_table.rowCount() == initial_rows + 1
    
    app.tasks_table.selectRow(0)
    qtbot.mouseClick(app.delete_task_button, Qt.MouseButton.LeftButton)
    assert app.tasks_table.rowCount() == initial_rows

def test_random_generation(app, qtbot):
    """Тест генерации случайных задач"""
    # Переключаемся на радио-кнопку случайной генерации
    app.random_radio.setChecked(True)
    app.random_count_spin.setValue(5)
    
    qtbot.mouseClick(app.generate_button, Qt.MouseButton.LeftButton)
    
    assert app.tasks_table.rowCount() == 5
    assert app.start_button.isEnabled()

def test_parameters_stagnation_special_text(app):
    """Проверка специального текста в SpinBox лимита стагнации"""
    app.stagnation_limit_spin.setValue(0)
    assert app.stagnation_limit_spin.specialValueText() == "Отключено"

def test_reset_function(app, qtbot):
    """Проверка кнопки сброса."""
    app.tasks_table.item(0, 1).setText("50")
    qtbot.mouseClick(app.clear_tasks_button, Qt.MouseButton.LeftButton)

    # После очистки таблица должна вернуться к исходному количеству пустых строк
    assert app.tasks_table.rowCount() == ui.TASK_TABLE_INITIAL_ROWS
    assert app.tasks_table.item(0, 1).text() == ""