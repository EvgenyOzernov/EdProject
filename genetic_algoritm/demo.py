from genetic_scheduler import Task, GAConfig, run_all, run_iter

tasks = [
    Task(id="A", duration=3, deadline=4),
    Task(id="B", duration=2, deadline=5),
    Task(id="C", duration=4, deadline=6),
    Task(id="D", duration=1, deadline=3),
]

config = GAConfig(
    population_size=10,
    generations=20,
    mutation_rate=0.3,
    crossover_rate=0.9,
    elite_count=1,
    tournament_size=3,
    random_seed=42,
)

result = run_all(tasks, config)

print("Лучший порядок:", result.best_solution.task_order)
print("Сумма задержек:", result.best_solution.total_tardiness)
print("История лучшего fitness:", result.best_fitness_history)
print("Причина остановки:", result.stop_reason)

for state in run_iter(tasks, config):
    print(
        "Поколение:", state.generation,
        "| Лучшее в поколении:", state.best_in_generation.total_tardiness,
        "| Лучшее глобально:", state.best_so_far.total_tardiness,
        "| Среднее:", round(state.average_fitness, 2),
    )
