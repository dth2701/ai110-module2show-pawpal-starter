"""PawPal demo.

Builds a small scenario — one owner, two pets, and several care tasks
added out of chronological order — then demonstrates the Scheduler's
sort_by_time() and the User's filter_tasks() methods in the terminal.
"""

from datetime import date

from pawpal_system import User, Pet, Scheduler, Task


def print_tasks(tasks) -> None:
    """Print a simple one-line summary for each task in `tasks`."""
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        print(f"  {task.start_time} — {task.name} "
              f"[priority: {task.priority}] [status: {task.status}]")


def main() -> None:
    today = date.today()

    # Owner and pets.
    user = User(user_id=1, full_name="Alex Rivera", email="alex@example.com", account="alex")
    biscuit = Pet(pet_id=1, name="Biscuit", date_of_birth=date(2020, 3, 10),
                  species="Golden Retriever")
    mochi = Pet(pet_id=2, name="Mochi", date_of_birth=date(2022, 8, 1),
                species="cat")
    user.add_pet(biscuit)
    user.add_pet(mochi)

    # Each pet gets a plan for today.
    biscuit_plan = Scheduler(date=today)
    mochi_plan = Scheduler(date=today)
    biscuit.add_plan(biscuit_plan)
    mochi.add_plan(mochi_plan)

    # Deliberately add tasks OUT of chronological order so sort_by_time()
    # has something to reorder. Every start time here is distinct across both
    # pets and fits the 8 AM-5 PM window, so every add should succeed.
    tasks = [
        (biscuit, biscuit_plan, Task(3, "Playtime", "14:00", 45, "fetch in yard", "low")),
        (biscuit, biscuit_plan, Task(1, "Morning walk", "08:00", 30, "long route", "high")),
        (biscuit, biscuit_plan, Task(2, "Feeding", "09:00", 10, "half cup kibble", "high")),
        (mochi, mochi_plan, Task(5, "Grooming", "11:00", 30, "brush coat", "low")),
        (mochi, mochi_plan, Task(4, "Feeding", "09:30", 15, "wet food", "high")),
    ]

    for pet, plan, task in tasks:
        _, message = user.add_task(pet, plan, task)
        print(message)

    # Conflict detection: try to schedule tasks at times that are already taken.
    # add_task blocks the clash and returns a warning message instead of crashing.
    print("\nConflict checks:")
    # Cross-pet: Biscuit is already fed at 09:00, so the owner can't also be
    # tending Mochi at 09:00 — one person, two places.
    _, message = user.add_task(
        mochi, mochi_plan, Task(6, "Litter change", "09:00", 10, "scoop box", "medium"))
    print(f"  {message}")
    # Same pet: Biscuit already has Playtime at 14:00.
    _, message = user.add_task(
        biscuit, biscuit_plan, Task(7, "Training", "14:00", 20, "sit and stay", "medium"))
    print(f"  {message}")

    # Mark a couple of tasks complete so the status filter has something to show.
    biscuit_plan.tasks[1].mark_task_complete()  # Morning walk
    mochi_plan.tasks[1].mark_task_complete()    # Mochi's Feeding

    # sort_by_time(): Biscuit's tasks were added 14:00, 08:00, 09:00 — the
    # method returns them in clock order regardless of insertion order.
    print("Biscuit's plan in insertion order:")
    print_tasks(biscuit_plan.tasks)

    print("\nBiscuit's plan in sorted time:")
    print_tasks(biscuit_plan.sort_by_time())

    # filter_tasks(): both filters are optional and combine with AND.
    print("\nAll completed tasks by complete status:")
    print_tasks(user.filter_tasks(status="complete"))

    print("\nAll of tasks filtered by pet name (Mochi):")
    print_tasks(user.filter_tasks(pet_name="Mochi"))

    print("\nBiscuit's pending tasks:")
    print_tasks(user.filter_tasks(status="pending", pet_name="Biscuit"))


if __name__ == "__main__":
    main()
