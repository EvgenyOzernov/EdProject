from __future__ import annotations

from dataclasses import dataclass
import random
from statistics import fmean
from typing import Iterator, Optional, Sequence


@dataclass(frozen=True)
class Task:
    # Описание одной задачи расписания.
    # id нужен GUI и пользователю для отображения порядка задач.
    # duration - время выполнения задачи.
    # deadline - срок, к которому желательно завершить задачу.
    id: str | int
    duration: int
    deadline: int


@dataclass(frozen=True)
class GAConfig:
    # Набор параметров генетического алгоритма, который может настраивать пользователь.
    # population_size - размер популяции в каждом поколении.
    # generations - максимальное число поколений после стартового.
    # mutation_rate - вероятность применить мутацию к потомку.
    # crossover_rate - вероятность выполнить скрещивание родителей.
    # elite_count - сколько лучших особей переносить в следующее поколение без изменений.
    # tournament_size - размер турнира при турнирной селекции.
    # selection_method, crossover_method, mutation_method - выбор операторов.
    # random_seed - фиксирует случайность для воспроизводимых запусков.
    # stagnation_limit - досрочная остановка, если лучший результат не улучшается.
    # history_enabled - нужно ли сохранять историю поколений в итоговом результате.
    population_size: int
    generations: int
    mutation_rate: float
    crossover_rate: float
    elite_count: int
    tournament_size: int
    selection_method: str = "tournament"
    crossover_method: str = "order_crossover"
    mutation_method: str = "swap"
    random_seed: Optional[int] = None
    stagnation_limit: Optional[int] = None
    history_enabled: bool = True


@dataclass
class Individual:
    # Внутреннее представление одной особи популяции.
    # chromosome - перестановка индексов задач.
    # fitness - значение целевой функции; чем меньше, тем лучше решение.
    chromosome: list[int]
    fitness: Optional[int] = None

    def copy(self) -> "Individual":
        return Individual(self.chromosome.copy(), self.fitness)


@dataclass(frozen=True)
class SolutionSnapshot:
    # Полное описание одного конкретного решения в удобном виде для GUI.
    # chromosome хранит внутреннюю перестановку индексов.
    # task_order - тот же порядок, но уже через пользовательские идентификаторы задач.
    # completion_times - моменты завершения задач в выбранном порядке.
    # tardiness_values - задержка каждой задачи: max(0, completion_time - deadline).
    # total_tardiness и fitness здесь совпадают, потому что оптимизируется сумма задержек.
    chromosome: tuple[int, ...]
    task_order: tuple[str | int, ...]
    completion_times: tuple[int, ...]
    tardiness_values: tuple[int, ...]
    total_tardiness: int
    fitness: int


@dataclass(frozen=True)
class GenerationState:
    # Снимок одного поколения.
    # GUI может брать такой объект и сразу строить визуализацию без дополнительных вычислений.
    # population содержит все текущие решения поколения.
    # best_in_generation - лучший кандидат текущего поколения.
    # best_so_far - лучший кандидат за все время работы алгоритма к этому шагу.
    # worst_fitness / average_fitness / fitness_values - данные для статистики популяции.
    # best_fitness_history - история лучшего найденного значения по поколениям для графика.
    generation: int
    population: tuple[SolutionSnapshot, ...]
    best_in_generation: SolutionSnapshot
    best_so_far: SolutionSnapshot
    worst_fitness: int
    average_fitness: float
    fitness_values: tuple[int, ...]
    best_fitness_history: tuple[int, ...]


@dataclass(frozen=True)
class RunResult:
    # Итог полного запуска алгоритма.
    # history - сохраненные состояния поколений для пошагового просмотра и возврата назад.
    # best_solution - финально лучшее найденное расписание.
    # best_fitness_history - готовый ряд для графика изменения качества решения.
    # stopped_early и stop_reason - информация о том, завершился ли запуск досрочно.
    history: tuple[GenerationState, ...]
    best_solution: SolutionSnapshot
    best_fitness_history: tuple[int, ...]
    stopped_early: bool
    stop_reason: str


def evaluate_schedule(
    tasks: Sequence[Task], chromosome: Sequence[int]
) -> SolutionSnapshot:
    # Преобразуем перестановку задач в конкретное расписание и считаем сумму задержек.
    # Идея такая:
    # 1. Идем по задачам в порядке, заданном хромосомой.
    # 2. Накапливаем текущее время завершения.
    # 3. Для каждой задачи считаем, насколько она опоздала относительно deadline.
    # 4. Суммируем все задержки - это и есть целевая функция минимизации.
    completion_time = 0
    task_order: list[str | int] = []
    completion_times: list[int] = []
    tardiness_values: list[int] = []

    for task_index in chromosome:
        task = tasks[task_index]
        completion_time += task.duration
        tardiness = max(0, completion_time - task.deadline)
        task_order.append(task.id)
        completion_times.append(completion_time)
        tardiness_values.append(tardiness)

    total_tardiness = sum(tardiness_values)
    chromosome_tuple = tuple(chromosome)
    task_order_tuple = tuple(task_order)
    completion_tuple = tuple(completion_times)
    tardiness_tuple = tuple(tardiness_values)
    return SolutionSnapshot(
        chromosome=chromosome_tuple,
        task_order=task_order_tuple,
        completion_times=completion_tuple,
        tardiness_values=tardiness_tuple,
        total_tardiness=total_tardiness,
        fitness=total_tardiness,
    )


def run_iter(tasks: Sequence[Task], config: GAConfig) -> Iterator[GenerationState]:
    # Пошаговый режим для GUI:
    # возвращаем состояния поколений по одному через yield.
    engine = _GAEngine(tasks, config)
    yield from engine.iter_states()


def run_all(tasks: Sequence[Task], config: GAConfig) -> RunResult:
    # Полный режим:
    # запускаем тот же механизм, но сразу собираем все шаги и возвращаем итог.
    engine = _GAEngine(tasks, config)
    history = tuple(engine.iter_states())
    return engine.build_result(history)


class _GAEngine:
    # Внутренний объект, управляющий всем жизненным циклом генетического алгоритма.
    # Внешнему коду достаточно использовать run_iter() или run_all().
    def __init__(self, tasks: Sequence[Task], config: GAConfig) -> None:
        self.tasks = tuple(tasks)
        self.config = config
        self._validate_inputs()
        self.random = random.Random(config.random_seed)
        self.best_history: list[int] = []
        self.best_so_far: Optional[Individual] = None
        self.stopped_early = False
        self.stop_reason = "completed_generations"

    def iter_states(self) -> Iterator[GenerationState]:
        # Сначала строим и оцениваем стартовую популяцию, чтобы GUI мог показать нулевое поколение.
        population = self._initialize_population()
        self._evaluate_population(population)

        initial_state = self._build_generation_state(generation=0, population=population)
        yield initial_state

        stagnation = 0
        for generation in range(1, self.config.generations + 1):
            # На каждом шаге создаем новое поколение, оцениваем его и отдаем полный снимок состояния.
            # Логика шага:
            # 1. Сохраняем часть лучших решений (элита).
            # 2. Выбираем родителей.
            # 3. Получаем потомков через crossover.
            # 4. Случайно изменяем некоторых потомков через mutation.
            # 5. Снова считаем качество всех особей.
            population = self._next_generation(population)
            self._evaluate_population(population)
            previous_best = self.best_history[-1]
            state = self._build_generation_state(generation=generation, population=population)
            yield state

            if state.best_so_far.fitness < previous_best:
                stagnation = 0
            else:
                # Если глобально лучший результат не улучшился, увеличиваем счетчик стагнации.
                stagnation += 1

            if (
                self.config.stagnation_limit is not None
                and stagnation >= self.config.stagnation_limit
            ):
                # Досрочно завершаем поиск, если много поколений подряд нет улучшения.
                self.stopped_early = True
                self.stop_reason = "stagnation_limit_reached"
                break

    def build_result(self, history: Sequence[GenerationState]) -> RunResult:
        # Собираем финальный объект результата после полного прогона.
        if not history:
            raise RuntimeError("Algorithm did not produce any generation states.")
        stored_history = tuple(history) if self.config.history_enabled else tuple()
        return RunResult(
            history=stored_history,
            best_solution=history[-1].best_so_far,
            best_fitness_history=history[-1].best_fitness_history,
            stopped_early=self.stopped_early,
            stop_reason=self.stop_reason,
        )

    def _validate_inputs(self) -> None:
        # Проверяем входные данные заранее, чтобы ошибки проявлялись сразу и понятно.
        if not self.tasks:
            raise ValueError("At least one task is required.")

        for task in self.tasks:
            if task.duration <= 0:
                raise ValueError("Task duration must be positive.")
            if task.deadline < 0:
                raise ValueError("Task deadline must be non-negative.")

        if self.config.population_size <= 0:
            raise ValueError("Population size must be positive.")
        if self.config.generations <= 0:
            raise ValueError("Generations count must be positive.")
        if self.config.elite_count < 0:
            raise ValueError("Elite count must be non-negative.")
        if self.config.elite_count >= self.config.population_size:
            raise ValueError("Elite count must be smaller than population size.")
        if self.config.tournament_size <= 0:
            raise ValueError("Tournament size must be positive.")
        if self.config.tournament_size > self.config.population_size:
            raise ValueError("Tournament size cannot exceed population size.")
        if not 0 <= self.config.mutation_rate <= 1:
            raise ValueError("Mutation rate must be between 0 and 1.")
        if not 0 <= self.config.crossover_rate <= 1:
            raise ValueError("Crossover rate must be between 0 and 1.")
        if self.config.stagnation_limit is not None and self.config.stagnation_limit <= 0:
            raise ValueError("Stagnation limit must be positive when provided.")

        if self.config.selection_method != "tournament":
            raise ValueError(f"Unsupported selection method: {self.config.selection_method}")

        supported_crossovers = {"order_crossover", "pmx"}
        if self.config.crossover_method not in supported_crossovers:
            raise ValueError(
                f"Unsupported crossover method: {self.config.crossover_method}"
            )

        supported_mutations = {"swap", "inversion"}
        if self.config.mutation_method not in supported_mutations:
            raise ValueError(f"Unsupported mutation method: {self.config.mutation_method}")

    def _initialize_population(self) -> list[Individual]:
        # Начальная популяция состоит из случайных перестановок всех задач.
        # Каждая особь - это один возможный порядок выполнения всех задач.
        base_chromosome = list(range(len(self.tasks)))
        population: list[Individual] = []
        for _ in range(self.config.population_size):
            chromosome = base_chromosome.copy()
            self.random.shuffle(chromosome)
            population.append(Individual(chromosome=chromosome))
        return population

    def _evaluate_population(self, population: Sequence[Individual]) -> None:
        # Для каждой особи вычисляем значение целевой функции.
        # Чем меньше fitness, тем лучше порядок выполнения задач.
        for individual in population:
            snapshot = evaluate_schedule(self.tasks, individual.chromosome)
            individual.fitness = snapshot.fitness

    def _build_generation_state(
        self, generation: int, population: Sequence[Individual]
    ) -> GenerationState:
        # Каждый снимок поколения содержит готовые данные для визуализации без пересчета в GUI.
        # Здесь же обновляется глобально лучшее решение за весь запуск.
        ordered_population = [evaluate_schedule(self.tasks, ind.chromosome) for ind in population]
        fitness_values = tuple(snapshot.fitness for snapshot in ordered_population)
        best_in_generation = min(ordered_population, key=lambda snapshot: snapshot.fitness)

        current_best_individual = min(population, key=lambda individual: self._fitness_of(individual))
        if self.best_so_far is None or self._fitness_of(current_best_individual) < self._fitness_of(
            self.best_so_far
        ):
            # Обновляем рекорд только если нашли действительно лучшее решение.
            self.best_so_far = current_best_individual.copy()

        best_so_far_snapshot = evaluate_schedule(self.tasks, self.best_so_far.chromosome)
        self.best_history.append(best_so_far_snapshot.fitness)

        return GenerationState(
            generation=generation,
            population=tuple(ordered_population),
            best_in_generation=best_in_generation,
            best_so_far=best_so_far_snapshot,
            worst_fitness=max(fitness_values),
            average_fitness=fmean(fitness_values),
            fitness_values=fitness_values,
            best_fitness_history=tuple(self.best_history),
        )

    def _next_generation(self, population: Sequence[Individual]) -> list[Individual]:
        # Элита копируется без изменений, остальные особи создаются через селекцию, скрещивание и мутацию.
        sorted_population = sorted(population, key=lambda individual: self._fitness_of(individual))
        next_population = [individual.copy() for individual in sorted_population[: self.config.elite_count]]

        while len(next_population) < self.config.population_size:
            # Выбираем двух родителей из текущей популяции.
            parent_a = self._select_parent(population)
            parent_b = self._select_parent(population)

            # Получаем двух потомков; для перестановок нужны специальные операторы,
            # чтобы не потерять задачи и не получить дубликаты.
            child_a_chromosome, child_b_chromosome = self._crossover(
                parent_a.chromosome, parent_b.chromosome
            )
            # Мутация добавляет разнообразие и помогает выходить из локальных минимумов.
            child_a_chromosome = self._mutate(child_a_chromosome)
            child_b_chromosome = self._mutate(child_b_chromosome)

            next_population.append(Individual(child_a_chromosome))
            if len(next_population) < self.config.population_size:
                next_population.append(Individual(child_b_chromosome))

        return next_population

    def _select_parent(self, population: Sequence[Individual]) -> Individual:
        if self.config.selection_method == "tournament":
            # Турнирная селекция: случайно выбираем несколько особей и берем лучшую из них.
            # Это простой и популярный способ сохранить давление отбора,
            # не сортируя популяцию при каждом выборе родителя.
            candidates = self.random.sample(list(population), self.config.tournament_size)
            return min(candidates, key=lambda individual: self._fitness_of(individual)).copy()
        raise ValueError(f"Unsupported selection method: {self.config.selection_method}")

    def _crossover(
        self, parent_a: Sequence[int], parent_b: Sequence[int]
    ) -> tuple[list[int], list[int]]:
        # Для хромосом-перестановок обычный побитовый crossover не подходит,
        # поэтому используем специальные операторы OX или PMX.
        if len(parent_a) < 2:
            return list(parent_a), list(parent_b)

        if self.random.random() > self.config.crossover_rate:
            return list(parent_a), list(parent_b)

        if self.config.crossover_method == "order_crossover":
            return self._order_crossover(parent_a, parent_b)
        if self.config.crossover_method == "pmx":
            return self._pmx_crossover(parent_a, parent_b)
        raise ValueError(f"Unsupported crossover method: {self.config.crossover_method}")

    def _mutate(self, chromosome: Sequence[int]) -> list[int]:
        # Мутация применяется не всегда, а только с вероятностью mutation_rate.
        result = list(chromosome)
        if len(result) < 2 or self.random.random() > self.config.mutation_rate:
            return result

        if self.config.mutation_method == "swap":
            return self._swap_mutation(result)
        if self.config.mutation_method == "inversion":
            return self._inversion_mutation(result)
        raise ValueError(f"Unsupported mutation method: {self.config.mutation_method}")

    def _order_crossover(
        self, parent_a: Sequence[int], parent_b: Sequence[int]
    ) -> tuple[list[int], list[int]]:
        # OX сохраняет фрагмент одного родителя, а остальную часть заполняет вторым в его порядке.
        left, right = sorted(self.random.sample(range(len(parent_a)), 2))
        child_a = self._order_crossover_one(parent_a, parent_b, left, right)
        child_b = self._order_crossover_one(parent_b, parent_a, left, right)
        return child_a, child_b

    def _order_crossover_one(
        self,
        base_parent: Sequence[int],
        fill_parent: Sequence[int],
        left: int,
        right: int,
    ) -> list[int]:
        # Сначала копируем выбранный сегмент base_parent,
        # затем слева направо подставляем недостающие элементы из fill_parent.
        child = [None] * len(base_parent)
        child[left : right + 1] = base_parent[left : right + 1]
        fill_values = [gene for gene in fill_parent if gene not in child]

        fill_index = 0
        for position in range(len(child)):
            if child[position] is None:
                child[position] = fill_values[fill_index]
                fill_index += 1

        return [int(gene) for gene in child]

    def _pmx_crossover(
        self, parent_a: Sequence[int], parent_b: Sequence[int]
    ) -> tuple[list[int], list[int]]:
        # PMX тоже копирует центральный сегмент, но оставшуюся часть восстанавливает
        # через частичное отображение между двумя родителями.
        left, right = sorted(self.random.sample(range(len(parent_a)), 2))
        child_a = self._pmx_crossover_one(parent_a, parent_b, left, right)
        child_b = self._pmx_crossover_one(parent_b, parent_a, left, right)
        return child_a, child_b

    def _pmx_crossover_one(
        self,
        base_parent: Sequence[int],
        other_parent: Sequence[int],
        left: int,
        right: int,
    ) -> list[int]:
        # PMX сохраняет центральный сегмент и восстанавливает корректную перестановку через отображение.
        child = [None] * len(base_parent)
        child[left : right + 1] = base_parent[left : right + 1]

        for index in range(left, right + 1):
            # Если элемент из второго родителя уже присутствует в скопированном сегменте,
            # ничего делать не нужно. Иначе ищем допустимую позицию по цепочке отображений.
            candidate = other_parent[index]
            if candidate in child:
                continue

            target_index = index
            while True:
                mapped_value = base_parent[target_index]
                target_index = other_parent.index(mapped_value)
                if child[target_index] is None:
                    child[target_index] = candidate
                    break

        for index in range(len(base_parent)):
            # Все еще пустые позиции просто заполняем значениями второго родителя.
            if child[index] is None:
                child[index] = other_parent[index]

        return [int(gene) for gene in child]

    def _swap_mutation(self, chromosome: list[int]) -> list[int]:
        # Swap mutation меняет местами две случайные задачи.
        left, right = self.random.sample(range(len(chromosome)), 2)
        chromosome[left], chromosome[right] = chromosome[right], chromosome[left]
        return chromosome

    def _inversion_mutation(self, chromosome: list[int]) -> list[int]:
        # Inversion mutation разворачивает случайный подотрезок перестановки.
        left, right = sorted(self.random.sample(range(len(chromosome)), 2))
        chromosome[left : right + 1] = reversed(chromosome[left : right + 1])
        return chromosome

    @staticmethod
    def _fitness_of(individual: Individual) -> int:
        # Внутренняя проверка: к моменту сравнения особь уже должна быть оценена.
        if individual.fitness is None:
            raise RuntimeError("Individual fitness must be evaluated before use.")
        return individual.fitness


__all__ = [
    "GAConfig",
    "GenerationState",
    "Individual",
    "RunResult",
    "SolutionSnapshot",
    "Task",
    "evaluate_schedule",
    "run_all",
    "run_iter",
]
