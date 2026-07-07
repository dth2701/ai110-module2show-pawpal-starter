# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
Daily plan for Biscuit (Golden Retriever):
  08:00 — Morning walk (30 min) [priority: high]
  09:00 — Feeding (10 min) [priority: high]
  14:00 — Playtime (45 min) [priority: low]

Daily plan for Mochi (cat):
  09:00 — Feeding (15 min) [priority: high]
  11:00 — Grooming (30 min) [priority: low]
```

## 🧪 Testing PawPal+

```bash
 python -m pytest
```

Sample test output:

```
(.venv) (base) ➜  ai110-module2show-pawpal-starter git:(main) python -m pytest
============================================ test session starts =============================================
platform darwin -- Python 3.11.5, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/tdo/Desktop/AI110/Module 2/ai110-module2show-pawpal-starter
plugins: anyio-4.14.1
collected 24 items                                                                                           

tests/test_pawpal.py ........................                                                          [100%]

============================================= 24 passed in 0.01s =============================================
```

- Foundations (2): completing a task flips its status; adding a task bumps the pet's task count.

- Sorting (7): chronological order, unpadded hours ("8:00" before "14:00"), no mutation, empty plan, priority-before-time, tie-break by time, unknown priority sorts last.

- Recurrence (7): daily→next day, weekly→+7 days, "once"→none, bad frequency→no recur, fields copied but reset to pending, no-due-date anchors to today, reused task_id.

- Conflicts (8): overlap rejected, adjacent allowed, 8am–5pm window, same-start clash across pets, unpadded-time match, ignores self, add_task blocks with a message, plus one documenting the cross-pet overlap gap.

- Confidence Level: 5 stars

## 📐 Smarter Scheduling

PawPal+ goes beyond a flat task list with four scheduling behaviors, each implemented by a named method in [pawpal_system.py](pawpal_system.py):

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Task sorting | `Scheduler.sort_by_time()`, `Scheduler.ordered_tasks()` | Chronological, or priority-first then chronological |
| Filtering | `User.filter_tasks()` | By pet name and/or completion status |
| Conflict handling | `Task.overlaps()`, `Scheduler.has_conflict()`, `User.check_conflicts()` | Overlaps within a plan and same-time clashes across the household |
| Recurring tasks | `Task.mark_task_complete()` | `once` / `daily` / `weekly` via the `RECURRENCE` map |


## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->
