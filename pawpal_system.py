"""PawPal system.

A small pet-care scheduler. The classes form a top-down ownership
hierarchy: a User owns Pets, each Pet has daily Plans, and each Plan
groups the Tasks scheduled for that day.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import List, Optional

# Fixed daily operating window for the app (8 AM - 5 PM).
OPENING_TIME = time(8, 0)
CLOSING_TIME = time(17, 0)

# Priority levels, ordered from most to least urgent. The rank is used to
# sort tasks so higher-priority items surface first in a plan.
PRIORITY_RANK = {"high": 0, "low": 1}


@dataclass
class Task:
    task_id: int
    name: str
    start_time: time
    duration: int  # minutes
    preferences: str
    priority: str  # "high" or "low"
    status: str = "pending"  # "pending" or "complete"

    def mark_complete(self) -> None:
        """Mark this task as complete."""
        self.status = "complete"

    def end_time(self) -> time:
        """Return the time this task finishes (start_time + duration)."""
        # `time` can't be added to directly, so anchor to an arbitrary
        # date, add the duration, then drop back to just the time.
        anchor = datetime.combine(date.min, self.start_time)
        return (anchor + timedelta(minutes=self.duration)).time()

    def overlaps(self, other: "Task") -> bool:
        """Return True if this task's time range overlaps with `other`."""
        # Two half-open ranges [start, end) overlap when each starts
        # before the other ends.
        return self.start_time < other.end_time() and other.start_time < self.end_time()


@dataclass
class Plan:
    date: date
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> bool:
        """Add a task to the plan.

        Return True if the task was added, False if it falls outside the
        8 AM-5 PM operating window or conflicts with an existing task.
        """
        if task.start_time < OPENING_TIME or task.end_time() > CLOSING_TIME:
            return False
        if self.has_conflict(task):
            return False
        self.tasks.append(task)
        return True

    def has_conflict(self, task: Task) -> bool:
        """Return True if `task` conflicts with an existing task in the plan."""
        return any(task.overlaps(existing) for existing in self.tasks)

    def ordered_tasks(self) -> List[Task]:
        """Return the plan's tasks ordered by start time.

        High-priority tasks are surfaced first so the owner sees them at
        the top; within each priority level tasks are sorted by start time.
        """
        return sorted(
            self.tasks,
            key=lambda t: (PRIORITY_RANK.get(t.priority, len(PRIORITY_RANK)), t.start_time),
        )


@dataclass
class Pet:
    pet_id: int
    name: str
    date_of_birth: date
    gender: str
    type: str
    plans: List[Plan] = field(default_factory=list)

    def add_plan(self, plan: Plan) -> None:
        """Add a plan to this pet."""
        self.plans.append(plan)

    def get_plan(self, day: date) -> Optional[Plan]:
        """Return the plan for the given date, or None if there isn't one."""
        for plan in self.plans:
            if plan.date == day:
                return plan
        return None

    def all_tasks(self) -> List[Task]:
        """Return every task across all of this pet's plans."""
        return [task for plan in self.plans for task in plan.tasks]


@dataclass
class User:
    user_id: int
    full_name: str
    email: str
    account: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this user."""
        self.pets.append(pet)

    def add_task(self, pet: Pet, plan: Plan, task: Task) -> bool:
        """Add a task to the given pet's plan.

        Return the result of the plan's scheduling check (True if the
        task fit and was added, False otherwise).
        """
        return plan.add_task(task)

    def edit_task(self, task: Task) -> bool:
        """Replace the stored task that shares `task`'s id with `task`.

        Searches every pet's plans for a task with the same task_id and
        swaps in the updated version. Returns True if one was found.
        """
        for pet in self.pets:
            for plan in pet.plans:
                for index, existing in enumerate(plan.tasks):
                    if existing.task_id == task.task_id:
                        plan.tasks[index] = task
                        return True
        return False

    def delete_task(self, plan: Plan, task: Task) -> bool:
        """Remove a task from the given plan. Return True if it was present."""
        if task in plan.tasks:
            plan.tasks.remove(task)
            return True
        return False

    def all_tasks(self) -> List[Task]:
        """Return every task across all of this user's pets' plans."""
        return [task for pet in self.pets for task in pet.all_tasks()]