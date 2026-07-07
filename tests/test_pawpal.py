"""Behavior tests for the PawPal system.

Grouped by the scheduling behaviors the README calls out: sorting, recurring
tasks, and conflict detection. Each group covers the tricky edge cases, not just
the happy path.
"""

from datetime import date, timedelta

from pawpal_system import Pet, Scheduler, Task, User


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_task(
    task_id=1,
    name="Walk",
    start="09:00",
    duration=30,
    priority="high",
    frequency="once",
    due_date=None,
):
    """Build a Task with sensible defaults so tests stay readable.

    start_time is an "HH:MM" string (all time math funnels through to_minutes).
    """
    return Task(
        task_id=task_id,
        name=name,
        start_time=start,
        duration=duration,
        preferences="none",
        priority=priority,
        frequency=frequency,
        due_date=due_date,
    )


def make_pet(pet_id=1, name="Rex"):
    """Build a Pet with the current fields (species, not gender/type)."""
    return Pet(
        pet_id=pet_id,
        name=name,
        date_of_birth=date(2020, 1, 1),
        species="dog",
    )


def make_user(*pets):
    """Build a User owning the given pets."""
    user = User(user_id=1, full_name="Sam", email="sam@example.com", account="free")
    for pet in pets:
        user.add_pet(pet)
    return user


# --------------------------------------------------------------------------- #
# Original behavior tests (previously broken against the implementation)
# --------------------------------------------------------------------------- #
def test_mark_complete_changes_status():
    """Task Completion: mark_task_complete() flips the task's status."""
    task = make_task()
    assert task.status == "pending"

    task.mark_task_complete()

    assert task.status == "complete"


def test_adding_task_increases_pet_task_count():
    """Task Addition: adding a task to a Pet raises that pet's task count."""
    pet = make_pet()
    plan = Scheduler(date=date(2026, 7, 1))
    pet.add_plan(plan)

    assert len(pet.all_tasks()) == 0

    added = plan.add_task(make_task())

    assert added is True
    assert len(pet.all_tasks()) == 1


# --------------------------------------------------------------------------- #
# A. Sorting  (Scheduler.sort_by_time / Scheduler.ordered_tasks)
# --------------------------------------------------------------------------- #
def test_sort_by_time_orders_chronologically():
    """The core case: tasks come back ascending by start time."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="14:00"),
        make_task(task_id=2, start="09:00"),
        make_task(task_id=3, start="11:30"),
    ]

    ordered = plan.sort_by_time()

    assert [t.start_time for t in ordered] == ["09:00", "11:30", "14:00"]


def test_sort_by_time_handles_unpadded_hours():
    """"8:00" must sort before "14:00" (int minutes, not raw string compare)."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="14:00"),
        make_task(task_id=2, start="8:00"),
    ]

    ordered = plan.sort_by_time()

    # Raw string compare would put "8:00" last ('8' > '1'); to_minutes fixes it.
    assert [t.start_time for t in ordered] == ["8:00", "14:00"]


def test_sort_by_time_does_not_mutate_original():
    """sort_by_time() returns a new list; the plan's own order is untouched."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="14:00"),
        make_task(task_id=2, start="09:00"),
    ]
    original = list(plan.tasks)

    plan.sort_by_time()

    assert plan.tasks == original


def test_sort_empty_scheduler_returns_empty():
    """Sorting an empty plan yields empty lists, not an error."""
    plan = Scheduler(date=date(2026, 7, 1))

    assert plan.sort_by_time() == []
    assert plan.ordered_tasks() == []


def test_ordered_tasks_priority_beats_time():
    """ordered_tasks ranks by priority first: a high 16:00 beats a low 08:00."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="08:00", priority="low"),
        make_task(task_id=2, start="16:00", priority="high"),
    ]

    ordered = plan.ordered_tasks()

    assert [t.priority for t in ordered] == ["high", "low"]


def test_ordered_tasks_ties_broken_by_time():
    """Within one priority, earlier start times come first."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="10:00", priority="high"),
        make_task(task_id=2, start="09:00", priority="high"),
    ]

    ordered = plan.ordered_tasks()

    assert [t.start_time for t in ordered] == ["09:00", "10:00"]


def test_ordered_tasks_unknown_priority_sorts_last():
    """Unrecognized priority (incl. miscased "High") falls to the end."""
    plan = Scheduler(date=date(2026, 7, 1))
    plan.tasks = [
        make_task(task_id=1, start="09:00", priority="High"),  # note: capitalized
        make_task(task_id=2, start="10:00", priority="low"),
    ]

    ordered = plan.ordered_tasks()

    # PRIORITY_RANK.get("High", 3) == 3 > rank("low") == 2, so "High" sorts last.
    assert [t.priority for t in ordered] == ["low", "High"]


# --------------------------------------------------------------------------- #
# B. Recurrence  (Task.mark_task_complete)
# --------------------------------------------------------------------------- #
def test_mark_complete_daily_creates_next_day():
    """The core case: completing a daily task returns the next day's occurrence."""
    task = make_task(frequency="daily", due_date=date(2026, 7, 1))

    nxt = task.mark_task_complete()

    assert task.status == "complete"
    assert isinstance(nxt, Task)
    assert nxt.status == "pending"
    assert nxt.due_date == date(2026, 7, 2)


def test_mark_complete_weekly_advances_seven_days():
    """A weekly task's next occurrence is due one week later."""
    task = make_task(frequency="weekly", due_date=date(2026, 7, 1))

    nxt = task.mark_task_complete()

    assert nxt.due_date == date(2026, 7, 8)


def test_mark_complete_once_returns_none():
    """A one-off task completes but has no follow-up to schedule."""
    task = make_task(frequency="once")

    nxt = task.mark_task_complete()

    assert task.status == "complete"
    assert nxt is None


def test_unknown_frequency_does_not_recur():
    """A frequency not in RECURRENCE (e.g. a typo) silently does not recur."""
    task = make_task(frequency="monthly")

    assert task.mark_task_complete() is None


def test_recurrence_preserves_fields_and_resets_status():
    """The next occurrence copies the task but is pending again."""
    task = make_task(
        name="Feed",
        start="12:00",
        duration=15,
        priority="medium",
        frequency="daily",
        due_date=date(2026, 7, 1),
    )

    nxt = task.mark_task_complete()

    assert nxt.name == "Feed"
    assert nxt.start_time == "12:00"
    assert nxt.duration == 15
    assert nxt.priority == "medium"
    assert nxt.frequency == "daily"
    assert nxt.status == "pending"


def test_recurrence_without_due_date_anchors_to_today():
    """With no due_date, the next occurrence is anchored to today, not the slot."""
    today = date.today()
    task = make_task(frequency="daily", due_date=None)

    nxt = task.mark_task_complete()

    assert nxt.due_date == today + timedelta(days=1)


def test_recurrence_reuses_task_id():
    """Limitation: the next occurrence reuses task_id, so edit/delete-by-id
    cannot tell the two occurrences apart."""
    task = make_task(task_id=42, frequency="daily", due_date=date(2026, 7, 1))

    nxt = task.mark_task_complete()

    assert nxt.task_id == task.task_id == 42


# --------------------------------------------------------------------------- #
# C. Conflict detection
#    (Task.overlaps / Scheduler.add_task / User.check_conflicts)
# --------------------------------------------------------------------------- #
def test_overlapping_task_rejected():
    """A task overlapping an existing one is not added."""
    plan = Scheduler(date=date(2026, 7, 1))
    assert plan.add_task(make_task(task_id=1, start="09:00", duration=30)) is True

    added = plan.add_task(make_task(task_id=2, start="09:15", duration=30))

    assert added is False
    assert len(plan.tasks) == 1


def test_adjacent_tasks_allowed():
    """Back-to-back tasks don't conflict: ranges are half-open [start, end)."""
    plan = Scheduler(date=date(2026, 7, 1))

    assert plan.add_task(make_task(task_id=1, start="09:00", duration=60)) is True
    assert plan.add_task(make_task(task_id=2, start="10:00", duration=60)) is True
    assert len(plan.tasks) == 2


def test_window_boundaries():
    """08:00 start and a 17:00 end are inside the window; just outside is rejected."""
    plan = Scheduler(date=date(2026, 7, 1))

    # Exactly on the open/close boundaries -> accepted.
    assert plan.add_task(make_task(task_id=1, start="08:00", duration=30)) is True
    assert plan.add_task(make_task(task_id=2, start="16:30", duration=30)) is True  # ends 17:00

    # Just outside -> rejected.
    assert plan.add_task(make_task(task_id=3, start="07:30", duration=30)) is False
    assert plan.add_task(make_task(task_id=4, start="17:00", duration=30)) is False  # ends 17:30


def test_check_conflicts_flags_same_start_across_pets():
    """The core case: the owner can't be in two places at the same minute."""
    day = date(2026, 7, 1)
    pet_a, pet_b = make_pet(pet_id=1, name="Rex"), make_pet(pet_id=2, name="Milo")
    plan_a, plan_b = Scheduler(date=day), Scheduler(date=day)
    pet_a.add_plan(plan_a)
    pet_b.add_plan(plan_b)
    task_a = make_task(task_id=1, name="Vet", start="09:00")
    plan_a.add_task(task_a)
    user = make_user(pet_a, pet_b)

    candidate = make_task(task_id=2, name="Groom", start="09:00")
    clashes = user.check_conflicts(pet_b, plan_b, candidate)

    assert len(clashes) == 1
    conflicting_task, owner = clashes[0]
    assert conflicting_task is task_a
    assert owner is pet_a


def test_check_conflicts_matches_unpadded_time():
    """"8:00" and "08:00" are the same minute, so they clash."""
    day = date(2026, 7, 1)
    pet = make_pet()
    plan = Scheduler(date=day)
    pet.add_plan(plan)
    plan.add_task(make_task(task_id=1, start="8:00"))
    user = make_user(pet)

    clashes = user.check_conflicts(pet, plan, make_task(task_id=2, start="08:00"))

    assert len(clashes) == 1


def test_check_conflicts_ignores_the_task_itself():
    """A task already on the plan is not reported as clashing with itself."""
    day = date(2026, 7, 1)
    pet = make_pet()
    plan = Scheduler(date=day)
    pet.add_plan(plan)
    task = make_task(task_id=1, start="09:00")
    plan.add_task(task)
    user = make_user(pet)

    assert user.check_conflicts(pet, plan, task) == []


def test_user_add_task_blocks_household_clash():
    """User.add_task refuses a clashing add and returns an explanatory message."""
    day = date(2026, 7, 1)
    pet = make_pet()
    plan = Scheduler(date=day)
    pet.add_plan(plan)
    plan.add_task(make_task(task_id=1, name="Vet", start="09:00"))
    user = make_user(pet)

    added, message = user.add_task(pet, plan, make_task(task_id=2, name="Groom", start="09:00"))

    assert added is False
    assert "Vet" in message  # message names the conflicting task
    assert len(plan.tasks) == 1

    # A clash-free add succeeds.
    ok, ok_message = user.add_task(pet, plan, make_task(task_id=3, name="Play", start="11:00"))
    assert ok is True
    assert "Play" in ok_message


def test_check_conflicts_misses_overlap_with_different_start_across_pets():
    """KNOWN LIMITATION: check_conflicts only matches identical start minutes.

    A cross-pet double-booking that overlaps but starts at a different minute
    (Rex 09:00-10:00, Milo 09:30-10:00) slips through, because check_conflicts
    compares start times for equality rather than testing overlap, and
    add_task's overlap check only looks at the target pet's own plan. This test
    pins the current (leaky) behavior so the gap is visible, not assumed fixed.
    """
    day = date(2026, 7, 1)
    pet_a, pet_b = make_pet(pet_id=1, name="Rex"), make_pet(pet_id=2, name="Milo")
    plan_a, plan_b = Scheduler(date=day), Scheduler(date=day)
    pet_a.add_plan(plan_a)
    pet_b.add_plan(plan_b)
    plan_a.add_task(make_task(task_id=1, start="09:00", duration=60))  # 09:00-10:00
    user = make_user(pet_a, pet_b)

    candidate = make_task(task_id=2, start="09:30", duration=30)  # overlaps, different start
    assert user.check_conflicts(pet_b, plan_b, candidate) == []
