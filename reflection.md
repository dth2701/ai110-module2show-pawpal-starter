# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.

My initial design centered on 4 classes arranged in a top-down ownership hierarchy: a User owns one or more Pets, each Pet has one or more care Plans, and each Plan groups one or more Tasks scheduled across a single day, reading top-down as User → Pet → Plan → Task. The Pet → Plan → Task links are strong "part-of" (composition) relationships — a plan and its tasks have no meaning apart from the pet they belong to, so they live and die with it. The User → Pet link is a weaker aggregation: a pet is a real animal that exists independently of any account, so ownership associates them without one owning the other's lifecycle. This mirrors the real-world structure of a pet-care app: a person managing the daily care routines of their animals.

- What classes did you include, and what responsibilities did you assign to each?

User — represents the pet owner. Attributes: user_id, full_name, email, account, and the pets they own. Its responsibility is managing the account and acting as the entry point for scheduling actions: a user can add, edit, and delete tasks on a pet's plan. Each user owns at least one pet.

Pet — represents an animal being cared for. Attributes: pet_id, name, date_of_birth, gender, and type (e.g., dog, cat, ...). Its responsibility is to hold identity and profile information and to own its care plans. Each pet has at least one plan.

Plan — represents a day's care schedule for a pet. Attributes: a date and the collection of tasks for that day. Its responsibility is to organize tasks in time: it enforces that there are no time conflicts between tasks and returns them in an order that surfaces priority tasks first so the owner sees them at the top. The 8 AM–5 PM operating window is a fixed constraint of the app rather than a per-task decision, so the plan simply schedules within it. Each plan contains at least one task.

Task — represents a single care activity (e.g., feeding, walking, grooming). Attributes: task_id, name, start_time, duration (how long it takes), preferences, and priority (yes/no). Its responsibility is to describe one unit of work and carry the data the scheduler needs — start_time plus duration to compute its end and detect overlaps for conflict checking, and the priority flag for ordering.

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

Yes, my design changed during implementation. The clearest change was making edit_task and delete_task consistent: my original UML had delete_task take both the Plan and Task but edit_task take only the Task, which meant editing had no way to know which plan the task lived in without scanning every pet and plan. I updated edit_task to also receive its Plan, so both methods locate the target the same way and the ownership path stays explicit. I also changed Pet.get_plan to return an optional Plan instead of always returning one, since a lookup for a date with no schedule should return nothing rather than fabricate an empty plan. These changes came from realizing that the method signatures, not just the class relationships.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

My scheduler enforces three constraints: the fixed 8am–5pm operating window, no time overlap within a pet's own plan, and no double-booking the same start time across the household. Priority (high/medium/low) and preferences are carried on each task but treated as ordering/display hints rather than hard blocks. I decided time validity mattered most because a schedule that physically can't happen is useless, so those checks hard-block an add, while priority only reorders what's already valid so the owner still sees the most urgent tasks first.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

The clearest tradeoff is in how I detect conflicts *across* pets. My scheduler actually has two layers of conflict checking. Within a single pet's plan, `Scheduler.add_task` uses `Task.overlaps` to do full interval overlap detection — it compares each task's whole `[start, end)` range, so a 9:00–9:30 walk correctly blocks a 9:15 feeding for the same pet. But the household-wide check, `User.check_conflicts` (which guards against the one owner being in two places at once), is deliberately coarser: it flags a clash only when two tasks across different pets share the *exact same start time*, compared as minutes so "8:00" and "08:00" match. It does not catch partial overlaps between pets — a 9:00–9:30 walk for Rex and a 9:15 feeding for Mia would slip through even though the owner can't physically do both at once.

- Why is that tradeoff reasonable for this scenario?

It's reasonable because the exact-start-time rule captures the most common and most confusing conflict — double-booking the same slot — with logic that is simple to reason about and easy to explain back to the owner ("that clashes with 'Walk' at 9:00 (Rex)"). Keeping the cross-pet check to a single start-time comparison also keeps that method small and readable, and avoids doing full O(range) overlap math across every other pet's plan on every add. For a lightweight home pet-care app where a person is realistically juggling a handful of pets and a few tasks a day, the exact-match rule blocks the mistakes people actually make, while the stricter overlap logic still protects each individual pet's own schedule. If the app grew toward tighter owner-availability guarantees, upgrading `check_conflicts` to reuse `Task.overlaps` (as the per-pet path already does) would be the natural next step.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I mainly used AI for design brainstorming and refactoring. Early on it helped me pressure-test the class hierarchy and method signatures, and later it helped me tighten the scheduling logic and time-handling code for readability without changing behavior.

- What kinds of prompts or questions were most helpful?

Open-ended prompts like "How could this algorithm be simplified for better readability or performance?" were the most useful, because they surfaced options rather than a single fix. Asking it to explain the tradeoffs of a change, instead of just applying one, let me keep the decision in my own hands.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

When refactoring conflict detection, AI suggested making the cross-pet `check_conflicts` do full interval-overlap math like the per-pet path. I chose not to, because the exact-start-time rule was simpler to explain to the owner and matched the mistakes people actually make, so I kept the coarser check and documented the gap instead.

- How did you evaluate or verify what the AI suggested?

I read through every suggested change line by line before accepting it, rather than applying anything wholesale. I also leaned on the test suite — running the sorting, recurrence, and conflict tests confirmed a refactor preserved behavior, and I even added a test that pins the known cross-pet limitation so the gap stays visible.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

I tested three behavior groups: sorting (chronological and priority-first ordering, including unpadded hours like "8:00"), recurrence (daily/weekly follow-ups, one-off tasks returning None, and unknown frequencies not recurring), and conflict detection (overlap rejection, adjacent tasks allowed, the 8am–5pm window boundaries, and same-start clashes across pets). Each group targets the tricky edge cases, not just the happy path.

- Why were these tests important?

These behaviors are the core scheduling logic — if sorting, recurrence, or conflict checks are wrong, the whole plan misleads the owner. Testing the edge cases (boundary times, unpadded hours, self-clash) protects against the subtle bugs that a happy-path demo would hide.

**b. Confidence**

- How confident are you that your scheduler works correctly?

I'm fairly confident for the intended single-owner, few-pets use case, since all sorting, recurrence, and conflict tests pass and I have a test that deliberately pins the one known limitation. My confidence is bounded, though: I know cross-pet partial overlaps at different start times slip past `check_conflicts`, so it's correct within its documented scope rather than airtight.

- What edge cases would you test next if you had more time?

I'd test cross-pet partial overlaps (the documented gap), tasks that span awkwardly against the closing boundary, and editing a recurring task whose reused task_id collides with its next occurrence. I'd also add tests for filtering combinations and for adding many tasks in one day to check ordering stays stable.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I'm most satisfied with the conflict-detection design. Splitting it into a strict per-pet overlap check and a deliberately simpler household-wide same-start-time check let me block the mistakes people actually make while keeping the logic easy to explain, and I like that the code is honest about the one case it doesn't catch.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I'd upgrade `check_conflicts` to reuse `Task.overlaps` so cross-pet partial overlaps are caught, closing the documented gap. I'd also give recurring tasks their own unique ids instead of reusing the parent's, so edit- and delete-by-id can tell two occurrences apart.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

The biggest lesson was to understand the requirements and the basic structure of the system before locking in a design, because a small misunderstanding forces changes that ripple through the classes and method signatures later. Thinking harder up front about what the app actually needs would have saved me from reworking method signatures and algorithms after the fact.
