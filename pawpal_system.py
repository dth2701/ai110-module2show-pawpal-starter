"""PawPal system.

A small pet-care scheduler. The classes form a top-down ownership
hierarchy: a User owns Pets, each Pet has daily Schedulers, and each Scheduler
groups the Tasks scheduled for that day.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional, Tuple

# How far ahead the next occurrence of a recurring task falls, keyed by
# frequency. A frequency not in this map (e.g. "once") does not recur.
RECURRENCE = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),  # weeks=1 is the same as days=7
}

# Fixed daily operating window for the app (8 AM - 5 PM), as "HH:MM" strings.
OPENING_TIME = "08:00"
CLOSING_TIME = "17:00"

# Priority levels, ordered from most to least urgent. The rank is used to
# sort tasks so higher-priority items surface first in a plan.
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def to_minutes(hhmm: str) -> int:
    """Convert an "HH:MM" clock string into minutes since midnight.

    All time math in the app funnels through here so times are compared and
    added as plain integers ("09:30" -> 570). Working in integers sidesteps
    the traps of raw "HH:MM" string comparison, which only sorts correctly
    when the hour is zero-padded.
    """
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


def to_hhmm(minutes: int) -> str:
    """Convert minutes since midnight back into a zero-padded "HH:MM" string."""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    task_id: int
    name: str
    start_time: str  # "HH:MM", 24-hour
    duration: int  # minutes
    preferences: str
    priority: str  # "high", "medium", or "low"
    status: str = "pending"  # "pending" or "complete"
    frequency: str = "once"  # "once", "daily", or "weekly"
    due_date: Optional[date] = None

    def mark_task_complete(self) -> Optional["Task"]:
        """Mark this task complete and, if it recurs, return the next occurrence.

        Sets this task's status to "complete". For a "daily" or "weekly" task,
        builds and returns a fresh, still-"pending" Task whose due_date is
        advanced by one interval. Returns None for a one-off ("once") task, so
        the caller can tell whether there is a follow-up task to schedule.
        """
        self.status = "complete"

        interval = RECURRENCE.get(self.frequency)
        if interval is None:
            return None  # one-off task: nothing to reschedule
        
        base = self.due_date or date.today()
        return Task(
            task_id=self.task_id,
            name=self.name,
            start_time=self.start_time,
            duration=self.duration,
            preferences=self.preferences,
            priority=self.priority,
            status="pending",
            frequency=self.frequency,
            due_date=base + interval,
        )

    def end_time(self) -> str:
        """Return the "HH:MM" time this task finishes (start_time + duration)."""
        return to_hhmm(to_minutes(self.start_time) + self.duration)

    def overlaps(self, other: "Task") -> bool:
        """Return True if this task's time range overlaps with `other`."""
        # Compare as minutes since midnight. Two half-open ranges
        # [start, end) overlap when each starts before the other ends.
        return (
            to_minutes(self.start_time) < to_minutes(other.end_time())
            and to_minutes(other.start_time) < to_minutes(self.end_time())
        )


@dataclass
class Scheduler:
    date: date
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> bool:
        """Add a task to the plan.

        Return True if the task was added, False if it falls outside the
        8 AM-5 PM operating window or conflicts with an existing task.
        """
        if (
            to_minutes(task.start_time) < to_minutes(OPENING_TIME)
            or to_minutes(task.end_time()) > to_minutes(CLOSING_TIME)
        ):
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
            key=lambda t: (PRIORITY_RANK.get(t.priority, len(PRIORITY_RANK)), to_minutes(t.start_time)),
        )

    def sort_by_time(self) -> List[Task]:
        """Return the tasks sorted chronologically by their "HH:MM" start_time.

        The lambda key converts each start_time to minutes since midnight
        ("09:30" -> 570) so tasks sort by clock time. Converting to an int is
        safer than comparing the strings directly: raw string comparison only
        works when the hour is zero-padded (so "8:00" would wrongly sort after
        "14:00", since '8' > '1').
        """
        return sorted(self.tasks, key=lambda task: to_minutes(task.start_time))


@dataclass
class Pet:
    pet_id: int
    name: str
    date_of_birth: date
    species: str
    plans: List[Scheduler] = field(default_factory=list)

    def add_plan(self, plan: Scheduler) -> None:
        """Add a plan to this pet."""
        self.plans.append(plan)

    def get_plan(self, day: date) -> Optional[Scheduler]:
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

    def check_conflicts(self, pet: Pet, plan: Scheduler, task: Task) -> List[Tuple[Task, Pet]]:
        """Find already-scheduled tasks that start at the same time as `task`.

        Looks across the whole household on the plan's date: the target pet's
        own plan (a pet can't do two things at the same minute) and every OTHER
        pet's plan for that date (the one owner can't be in two places at once).
        Start times are compared as minutes via to_minutes(), so "8:00" and
        "08:00" match. Returns a list of (conflicting_task, owning_pet) pairs;
        an empty list means there is no clash. Pure read - never raises.
        """
        start = to_minutes(task.start_time)
        clashes: List[Tuple[Task, Pet]] = []
        for owner in self.pets:
            # Target pet: use the given plan (task may not be added yet).
            # Other pets: their plan for the same date, if any.
            owner_plan = plan if owner is pet else owner.get_plan(plan.date)
            if owner_plan is None:
                continue
            # Skip the task itself in case it's already on the plan.
            for existing in owner_plan.tasks:
                if existing is not task and to_minutes(existing.start_time) == start:
                    clashes.append((existing, owner))
        return clashes

    def add_task(self, pet: Pet, plan: Scheduler, task: Task) -> Tuple[bool, str]:
        """Add a task to the given pet's plan, checking for time conflicts first.

        Returns (added, message). If another task - for this pet or any other
        pet - is already scheduled at the same start time, the task is NOT added
        and the message explains the clash. Otherwise the task goes through the
        plan's 8am-5pm window and overlap checks, and the message reports the
        outcome. Blocks the conflicting add rather than raising.
        """
        clashes = self.check_conflicts(pet, plan, task)
        if clashes:
            details = ", ".join(
                f"'{t.name}' at {t.start_time} ({p.name})" for t, p in clashes
            )
            return False, (
                f"⚠️ Can't schedule '{task.name}' at {task.start_time} for "
                f"{pet.name} — it clashes with {details}."
            )
        if plan.add_task(task):
            return True, f"Scheduled '{task.name}' for {pet.name} at {task.start_time}."
        return False, (
            f"Couldn't schedule '{task.name}' — it falls outside the 8am-5pm "
            f"window or overlaps another task on {pet.name}'s plan."
        )

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

    def delete_task(self, plan: Scheduler, task: Task) -> bool:
        """Remove a task from the given plan. Return True if it was present."""
        if task in plan.tasks:
            plan.tasks.remove(task)
            return True
        return False

    def all_tasks(self) -> List[Task]:
        """Return every task across all of this user's pets' plans."""
        return [task for pet in self.pets for task in pet.all_tasks()]

    def filter_tasks(
        self,
        status: Optional[str] = None,
        pet_name: Optional[str] = None,
    ) -> List[Task]:
        """Return tasks across all pets, filtered by status and/or pet name.

        Both filters are optional and combine with AND: a filter left as None
        matches everything, so `filter_tasks()` returns all tasks, while
        `filter_tasks(status="complete", pet_name="Rex")` returns only Rex's
        completed tasks.
        """
        results = []
        for pet in self.pets:
            if pet_name is not None and pet.name != pet_name:
                continue
            for task in pet.all_tasks():
                if status is not None and task.status != status:
                    continue
                results.append(task)
        return results