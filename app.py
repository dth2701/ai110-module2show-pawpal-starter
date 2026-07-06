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
        )

        # User.add_task checks for same-time conflicts (this pet and every other
        # pet) plus the plan's window/overlap rules, and returns (added, message).
        added, message = user.add_task(pet, plan, task)
        if added:
            st.session_state.next_task_id += 1
            st.success(message)
        else:
            st.error(message)

st.divider()

st.subheader("Build Schedule")
st.caption("The selected pet's plan for a day, ordered by priority then start time.")

if user.pets:
    view_pet_name = st.selectbox("Show schedule for", [p.name for p in user.pets], key="view_pet")
    view_day = st.date_input("On day", value=date.today(), key="view_day")

    view_pet = next(p for p in user.pets if p.name == view_pet_name)
    plan = view_pet.get_plan(view_day)

    if plan and plan.tasks:
        st.table(
            [
                {
                    "priority": t.priority,
                    "task": t.name,
                    "start": t.start_time,
                    "end": t.end_time(),
                    "status": t.status,
                }
                for t in plan.ordered_tasks()
            ]
        )
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

    if matches:
        st.table(
            [
                {
                    "priority": t.priority,
                    "task": t.name,
                    "start": t.start_time,
                    "end": t.end_time(),
                    "status": t.status,
                }
                for t in matches
            ]
        )
    else:
        st.info("No tasks match this filter.")
else:
    st.info("No pets yet. Add a pet and schedule a task above.")
