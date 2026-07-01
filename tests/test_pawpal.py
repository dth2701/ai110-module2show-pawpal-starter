"""Simple behavior tests for the PawPal system."""

from datetime import date, time

from pawpal_system import Pet, Plan, Task


def make_task(task_id=1, start=time(9, 0), duration=30, priority="high"):
    """Build a Task with sensible defaults so tests stay readable."""
    return Task(
        task_id=task_id,
        name="Walk",
        start_time=start,
        duration=duration,
        preferences="none",
        priority=priority,
    )


def test_mark_complete_changes_status():
    """Task Completion: mark_complete() flips the task's status."""
    task = make_task()
    assert task.status == "pending"

    task.mark_complete()

    assert task.status == "complete"


def test_adding_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet raises that pet's task count."""
    pet = Pet(
        pet_id=1,
        name="Rex",
        date_of_birth=date(2020, 1, 1),
        gender="male",
        type="dog",
    )
    plan = Plan(date=date(2026, 7, 1))
    pet.add_plan(plan)

    assert len(pet.all_tasks()) == 0

    added = plan.add_task(make_task())

    assert added is True
    assert len(pet.all_tasks()) == 1
