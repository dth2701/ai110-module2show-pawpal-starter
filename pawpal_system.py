"""PawPal system skeleton.

Class stubs generated from diagrams/uml.mmd. Method bodies are left as
`pass`/`NotImplementedError` stubs to be filled in later.
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import List, Optional


@dataclass
class Task:
    task_id: int
    name: str
    start_time: time
    duration: int  # minutes
    preferences: str
    priority: bool

    def end_time(self) -> time:
        """Return the time this task finishes (start_time + duration)."""
        raise NotImplementedError

    def overlaps(self, other: "Task") -> bool:
        """Return True if this task's time range overlaps with `other`."""
        raise NotImplementedError


@dataclass
class Plan:
    date: date
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> bool:
        """Add a task to the plan. Return True if added successfully."""
        raise NotImplementedError

    def has_conflict(self, task: Task) -> bool:
        """Return True if `task` conflicts with an existing task in the plan."""
        raise NotImplementedError

    def ordered_tasks(self) -> List[Task]:
        """Return the plan's tasks ordered by start time."""
        raise NotImplementedError


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
        raise NotImplementedError

    def get_plan(self, day: date) -> Optional[Plan]:
        """Return the plan for the given date, if one exists."""
        raise NotImplementedError


@dataclass
class User:
    user_id: int
    full_name: str
    email: str
    account: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this user."""
        raise NotImplementedError

    def add_task(self, pet: Pet, plan: Plan, task: Task) -> None:
        """Add a task to the given pet's plan."""
        raise NotImplementedError

    def edit_task(self, task: Task) -> None:
        """Edit an existing task."""
        raise NotImplementedError

    def delete_task(self, plan: Plan, task: Task) -> None:
        """Remove a task from the given plan."""
        raise NotImplementedError
