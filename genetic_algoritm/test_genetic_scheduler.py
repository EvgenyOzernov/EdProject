from genetic_scheduler import GAConfig, Task, evaluate_schedule, run_all, run_iter


def build_tasks():
    # Базовый набор задач для большинства тестов.
    return [
        Task(id="A", duration=3, deadline=4),
        Task(id="B", duration=2, deadline=5),
        Task(id="C", duration=4, deadline=6),
        Task(id="D", duration=1, deadline=3),
    ]


def build_config(**overrides):
    # Удобный конструктор стандартной конфигурации с возможностью точечно менять параметры.
    params = {
        "population_size": 8,
        "generations": 5,
        "mutation_rate": 0.4,
        "crossover_rate": 0.9,
        "elite_count": 1,
        "tournament_size": 3,
        "random_seed": 7,
    }
    params.update(overrides)
    return GAConfig(**params)


def assert_is_permutation(snapshot, tasks):
    # Проверяем, что решение содержит все задачи ровно по одному разу.
    assert sorted(snapshot.chromosome) == list(range(len(tasks)))
    assert sorted(snapshot.task_order) == sorted(task.id for task in tasks)


def test_evaluate_schedule_total_tardiness():
    # Проверка ручного примера:
    # функция оценки должна правильно посчитать моменты завершения,
    # индивидуальные задержки и их суммарное значение.
    tasks = [
        Task(id="A", duration=3, deadline=2),
        Task(id="B", duration=2, deadline=10),
        Task(id="C", duration=4, deadline=5),
    ]

    snapshot = evaluate_schedule(tasks, [0, 1, 2])

    assert snapshot.completion_times == (3, 5, 9)
    assert snapshot.tardiness_values == (1, 0, 4)
    assert snapshot.total_tardiness == 5
    assert snapshot.fitness == 5


def test_run_iter_contains_initial_generation():
    # Генератор пошагового режима обязан возвращать стартовое поколение с номером 0,
    # а также корректно накапливать историю лучшего fitness по поколениям.
    tasks = build_tasks()
    config = build_config(generations=4)

    states = list(run_iter(tasks, config))

    assert states[0].generation == 0
    assert len(states) == 5
    assert len(states[0].best_fitness_history) == 1
    assert len(states[-1].best_fitness_history) == len(states)


def test_population_snapshots_are_valid_permutations():
    # После OX-скрещивания и swap-мутации все особи должны оставаться
    # корректными перестановками без потерь и дубликатов задач.
    tasks = build_tasks()
    config = build_config(
        generations=3, crossover_method="order_crossover", mutation_method="swap"
    )

    states = list(run_iter(tasks, config))

    for state in states:
        for snapshot in state.population:
            assert_is_permutation(snapshot, tasks)


def test_population_snapshots_are_valid_with_pmx_and_inversion():
    # Аналогичная проверка для альтернативных операторов:
    # PMX-скрещивание и inversion-мутация тоже должны сохранять корректность перестановки.
    tasks = build_tasks()
    config = build_config(generations=3, crossover_method="pmx", mutation_method="inversion")

    states = list(run_iter(tasks, config))

    for state in states:
        for snapshot in state.population:
            assert_is_permutation(snapshot, tasks)


def test_random_seed_makes_run_reproducible():
    # При одинаковом random_seed алгоритм должен выдавать воспроизводимый результат.
    tasks = build_tasks()
    config = build_config(generations=6, random_seed=123)

    result_a = run_all(tasks, config)
    result_b = run_all(tasks, config)

    assert result_a.best_solution.chromosome == result_b.best_solution.chromosome
    assert result_a.best_fitness_history == result_b.best_fitness_history


def test_run_all_returns_full_history_and_best_solution():
    # Полный запуск должен возвращать:
    # 1. историю всех поколений,
    # 2. финально лучшее решение,
    # 3. историю значений best fitness,
    # 4. корректную информацию о причине завершения.
    tasks = build_tasks()
    config = build_config(generations=4)

    result = run_all(tasks, config)

    assert len(result.history) == 5
    assert result.best_solution == result.history[-1].best_so_far
    assert result.best_fitness_history == result.history[-1].best_fitness_history
    assert result.stopped_early is False
    assert result.stop_reason == "completed_generations"


def test_history_can_be_used_for_step_back_navigation():
    # История поколений должна позволять GUI "отматывать назад"
    # и брать снимок любого предыдущего шага по индексу.
    tasks = build_tasks()
    config = build_config(generations=5)

    result = run_all(tasks, config)

    earlier_state = result.history[2]
    later_state = result.history[-1]

    assert earlier_state.generation == 2
    assert later_state.generation == 5
    assert len(earlier_state.best_fitness_history) == 3


def test_stagnation_limit_stops_run_early():
    # Если лучший результат долго не улучшается, алгоритм должен завершиться досрочно
    # и явно сообщить причину остановки.
    tasks = [Task(id="only", duration=2, deadline=1)]
    config = build_config(
        population_size=4,
        generations=20,
        elite_count=0,
        tournament_size=2,
        stagnation_limit=3,
    )

    result = run_all(tasks, config)

    assert result.stopped_early is True
    assert result.stop_reason == "stagnation_limit_reached"
    assert len(result.history) == 4
    assert result.best_solution.total_tardiness == 1


def test_single_task_case_is_supported():
    # Крайний случай: одна задача.
    # Алгоритм не должен ломаться на кроссовере или мутации при длине хромосомы 1.
    tasks = [Task(id="A", duration=5, deadline=3)]
    config = build_config(
        population_size=3,
        generations=2,
        elite_count=0,
        tournament_size=1,
        crossover_rate=0.0,
        mutation_rate=0.0,
    )

    result = run_all(tasks, config)

    assert result.best_solution.task_order == ("A",)
    assert result.best_solution.total_tardiness == 2


def test_all_tasks_meet_deadlines_can_reach_zero_tardiness():
    # Если любой порядок укладывается в дедлайны, алгоритм должен уметь вернуть fitness = 0.
    tasks = [
        Task(id="A", duration=1, deadline=10),
        Task(id="B", duration=1, deadline=10),
        Task(id="C", duration=1, deadline=10),
    ]
    config = build_config(generations=3)

    result = run_all(tasks, config)

    assert result.best_solution.total_tardiness == 0


def test_same_deadlines_case_runs_correctly():
    # Отдельный сценарий с одинаковыми дедлайнами:
    # проверяем, что алгоритм стабильно работает и выдает корректную историю.
    tasks = [
        Task(id="A", duration=2, deadline=3),
        Task(id="B", duration=1, deadline=3),
        Task(id="C", duration=4, deadline=3),
    ]
    config = build_config(generations=4)

    result = run_all(tasks, config)

    assert len(result.history) == 5
    assert result.best_solution.total_tardiness >= 0


def test_history_disabled_returns_empty_stored_history():
    # Если сохранение истории отключено, итоговый результат не должен хранить поколения,
    # но история best fitness для финальной статистики все равно должна остаться доступной.
    tasks = build_tasks()
    config = build_config(history_enabled=False)

    result = run_all(tasks, config)

    assert result.history == ()
    assert len(result.best_fitness_history) == config.generations + 1
