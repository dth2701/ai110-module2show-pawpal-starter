from datetime import date, time

import streamlit as st

from pawpal_system import User, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner_name = st.text_input("Owner name", value="Jordan")

# Keep a single User object alive across Streamlit reruns. Everything the
# UI shows is a projection of this object's state.
if "user" not in st.session_state:
    st.session_state.user = User(user_id=1, full_name=owner_name, email="", account="")
user = st.session_state.user
user.full_name = owner_name

st.subheader("Add a Pet")
# A form batches the inputs and only submits on the button press, so we
# don't rebuild a Pet on every keystroke.
with st.form("add_pet_form"):
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])
    dob = st.date_input("Date of birth", value=date(2020, 1, 1))
    submitted = st.form_submit_button("Add pet")

if submitted:
    pet = Pet(
        pet_id=len(user.pets) + 1,
        name=pet_name,
        date_of_birth=dob,
        species=species,
    )
    user.add_pet(pet)  # the User method that owns this data
    st.success(f"Added {pet.name}!")

# Re-rendered on every rerun, so the newly added pet shows up immediately.
if user.pets:
    st.write("Your pets:")
    st.table(
        [
            {
                "id": p.pet_id,
                "name": p.name,
                "species": p.species,
                "born": p.date_of_birth,
            }
            for p in user.pets
        ]
    )
else:
    st.info("No pets yet. Add one above.")

st.divider()

st.markdown("### Schedule a Task")
st.caption("Pick a pet and a day, then add a task. It's checked against the 8am–5pm window and existing tasks.")

# Task ids must be unique and stable across reruns, so keep a counter here
# rather than deriving one from list length (which breaks after deletes).
if "next_task_id" not in st.session_state:
    st.session_state.next_task_id = 1

if not user.pets:
    st.info("Add a pet first — tasks are scheduled onto a specific pet's plan.")
else:
    with st.form("add_task_form"):
        # A task belongs to one pet's plan for one day.
        pet_name = st.selectbox("Pet", [p.name for p in user.pets])
        day = st.date_input("Day", value=date.today())

        col1, col2, col3 = st.columns(3)
        with col1:
            task_title = st.text_input("Task title", value="Morning walk")
            start_time = st.time_input("Start time", value=time(9, 0))
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            preferences = st.text_input("Preferences", value="")
        with col3:
            priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
            frequency = st.selectbox("Repeat", ["once", "daily", "weekly"], index=0)

        submitted_task = st.form_submit_button("Add task")

    if submitted_task:
        # Resolve the chosen pet, then get-or-create its plan for that day.
        pet = next(p for p in user.pets if p.name == pet_name)
        plan = pet.get_plan(day)
        if plan is None:
            plan = Scheduler(date=day)
            pet.add_plan(plan)

        task = Task(
            task_id=st.session_state.next_task_id,
            name=task_title,
            # The picker returns a `time`; the backend works in "HH:MM"
            # strings, so convert here at the boundary.
            start_time=start_time.strftime("%H:%M"),
            duration=int(duration),
            preferences=preferences,
            priority=priority,
            frequency=frequency,
            # Anchor recurrence to the scheduled day so mark_task_complete()
            # advances the next occurrence from the right date.
            due_date=day,
        )

        # User.add_task checks for same-time conflicts (this pet and every other
        # pet) plus the plan's window/overlap rules, and returns (added, message).
        added, message = user.add_task(pet, plan, task)
        if added:
            st.session_state.next_task_id += 1
            st.success(message)
            st.toast(f"Added '{task_title}' 🐾")
        else:
            # Hard block: the task was NOT scheduled. Red + a concrete fix.
            st.error(message)
            st.caption("Try a different start time, or shorten the task so it fits the 8am–5pm window.")

st.divider()

st.subheader("Build Schedule")
st.caption("The selected pet's plan for a day. Sort it, spot conflicts, and mark tasks done.")

# A one-shot message set just before an st.rerun() (e.g. after completing a
# recurring task) so the outcome survives the rerun and shows here.
if "flash" in st.session_state:
    kind, text = st.session_state.pop("flash")
    getattr(st, kind)(text)

if user.pets:
    view_pet_name = st.selectbox("Show schedule for", [p.name for p in user.pets], key="view_pet")
    view_day = st.date_input("On day", value=date.today(), key="view_day")
    # Two orderings the Scheduler exposes: by priority, or purely chronological.
    sort_mode = st.radio("Sort by", ["Priority", "Start time"], horizontal=True, key="sort_mode")

    view_pet = next(p for p in user.pets if p.name == view_pet_name)
    plan = view_pet.get_plan(view_day)

    # Household conflict check for the whole day. add_task blocks same-start-time
    # clashes, but two pets can still hold tasks that overlap at *different*
    # start times — Task.overlaps() catches those so the one owner sees them.
    day_tasks = [
        (p, t) for p in user.pets if p.get_plan(view_day) for t in p.get_plan(view_day).tasks
    ]
    clashes = [
        (pa, ta, pb, tb)
        for i, (pa, ta) in enumerate(day_tasks)
        for pb, tb in day_tasks[i + 1:]
        if ta.overlaps(tb)
    ]
    if clashes:
        # Soft warning (amber), not an error: both tasks stay scheduled. We're
        # telling the owner they'd be needed in two places at once, with enough
        # detail — and a concrete fix — to resolve it.
        st.warning(
            f"⚠️ **You're double-booked on {view_day:%b %d}.** "
            f"{len(clashes)} pair(s) of tasks overlap, so you'd be needed in two places at once."
        )
        with st.expander("Show the overlapping tasks", expanded=True):
            for pa, ta, pb, tb in clashes:
                st.markdown(
                    f"- **{pa.name} · {ta.name}** ({ta.start_time}–{ta.end_time()}) "
                    f"overlaps **{pb.name} · {tb.name}** ({tb.start_time}–{tb.end_time()})"
                )
            st.caption("Tip: stagger the start times or shorten one task so the two don't overlap.")
    elif day_tasks:
        # Reassure when the day is clean — as useful as flagging a clash.
        st.success("✅ No scheduling conflicts for this day.")

    if plan and plan.tasks:
        # Pick the Scheduler ordering that matches the toggle.
        tasks = plan.ordered_tasks() if sort_mode == "Priority" else plan.sort_by_time()

        st.caption(f"{len(tasks)} task(s), sorted by {sort_mode.lower()}.")
        # A clean, static table for the read view; the recurrence marker rides
        # in the task name so the schedule stays a single, scannable grid.
        st.table(
            [
                {
                    "priority": t.priority,
                    "task": t.name + (f"  🔁 {t.frequency}" if t.frequency != "once" else ""),
                    "start": t.start_time,
                    "end": t.end_time(),
                    "status": "✅ complete" if t.status == "complete" else "⏳ pending",
                }
                for t in tasks
            ]
        )

        # Actions live below the table so the schedule itself stays uncluttered.
        with st.expander("Manage a task"):
            # Index-based selection avoids duplicate-label collisions.
            idx = st.selectbox(
                "Select a task",
                range(len(tasks)),
                format_func=lambda i: f"{tasks[i].start_time} · {tasks[i].name}"
                + ("  ✅" if tasks[i].status == "complete" else ""),
                key="manage_task",
            )
            target = tasks[idx]
            mcol1, mcol2 = st.columns(2)
            done_clicked = mcol1.button(
                "✅ Mark done", key="mark_done", disabled=target.status == "complete"
            )
            del_clicked = mcol2.button("🗑️ Delete", key="del_task")

            if done_clicked:
                # mark_task_complete() flips status and, for a recurring task,
                # hands back the next occurrence to schedule.
                follow_up = target.mark_task_complete()
                if follow_up is not None:
                    next_day = follow_up.due_date
                    next_plan = view_pet.get_plan(next_day)
                    if next_plan is None:
                        next_plan = Scheduler(date=next_day)
                        view_pet.add_plan(next_plan)
                    # Give the follow-up its own id so it doesn't collide.
                    follow_up.task_id = st.session_state.next_task_id
                    added, msg = user.add_task(view_pet, next_plan, follow_up)
                    if added:
                        st.session_state.next_task_id += 1
                        st.session_state.flash = (
                            "success",
                            f"✅ Completed '{target.name}'. Next {target.frequency} occurrence set for {next_day}.",
                        )
                    else:
                        st.session_state.flash = (
                            "warning",
                            f"Completed '{target.name}', but couldn't auto-schedule the next occurrence: {msg}",
                        )
                else:
                    st.session_state.flash = ("success", f"✅ Marked '{target.name}' complete.")
                st.rerun()

            if del_clicked:
                user.delete_task(plan, target)
                st.session_state.flash = ("info", f"🗑️ Deleted '{target.name}'.")
                st.rerun()
    else:
        st.info("No tasks scheduled for this pet on this day yet.")
else:
    st.info("No pets yet. Add a pet and schedule a task above.")

st.divider()

st.subheader("Filter Tasks")
st.caption("Filter tasks across all days by completion status and/or pet, via User.filter_tasks().")

if user.pets:
    # "All" is the no-filter choice; it maps to None so filter_tasks() ignores
    # that dimension. The two dropdowns combine with AND.
    fcol1, fcol2 = st.columns(2)
    with fcol1:
        status_choice = st.selectbox("Status", ["All", "pending", "complete"], key="filter_status")
    with fcol2:
        pet_choice = st.selectbox("Pet", ["All"] + [p.name for p in user.pets], key="filter_pet")

    status_filter = None if status_choice == "All" else status_choice
    pet_filter = None if pet_choice == "All" else pet_choice

    matches = user.filter_tasks(status=status_filter, pet_name=pet_filter)

    # filter_tasks() returns bare Tasks, but this view spans every pet and day,
    # so map each task back to its owner to show a Pet column.
    task_owner = {id(t): p.name for p in user.pets for t in p.all_tasks()}

    if matches:
        # Sort the cross-day results by day, then start time (start_time is
        # zero-padded "HH:MM", so a plain string sort is chronological).
        matches = sorted(matches, key=lambda t: (t.due_date or date.min, t.start_time))
        done = sum(1 for t in matches if t.status == "complete")
        st.caption(f"{len(matches)} task(s) · {done} complete · {len(matches) - done} pending")
        st.table(
            [
                {
                    "pet": task_owner.get(id(t), "?"),
                    "day": t.due_date,
                    "priority": t.priority,
                    "task": t.name,
                    "start": t.start_time,
                    "end": t.end_time(),
                    "repeat": t.frequency,
                    "status": t.status,
                }
                for t in matches
            ]
        )
    else:
        st.info("No tasks match this filter.")
else:
    st.info("No pets yet. Add a pet and schedule a task above.")
