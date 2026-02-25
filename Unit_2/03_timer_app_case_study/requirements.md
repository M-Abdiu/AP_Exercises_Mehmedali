# Timer & Alarm Clock App — Software Requirements (v0.1)

Date: 2026-02-23

## Scope
This document specifies functional and non-functional requirements for a timer and alarm clock app that includes:
- Alarms
- Reminders at specific dates and times
- Countdown timer
- Pomodoro timer
- World clock
- Date/time conversions

Unless otherwise stated, “the system” refers to the application and its local data storage.

---

## 1) Elicitation

### 1.1 Source statement (provided)
- Goal: Develop a timer and alarm clock app including alarms, reminders at specific dates and times, a countdown timer, a pomodoro timer, a world clock, and date and time conversions.

### 1.2 Elicited needs
1. Users need to create alarms that trigger at times of day.
2. Users need to enable/disable, edit, and delete alarms.
3. Users need alarm notifications when an alarm triggers.
4. Users need reminders that trigger at specific date+time instants.
5. Users need to manage reminders (create/edit/delete/enable/disable).
6. Users need a countdown timer they can start, pause, resume, and cancel.
7. Users need a pomodoro timer (work/break cycles) with configurable durations.
8. Users need a world clock to view current time in multiple time zones.
9. Users need date/time conversions (e.g., between time zones and formats).
10. Users need persistence so configured items survive app restarts.
11. Users need correct behavior across time zones, DST changes, and system clock changes.
12. Users need basic usability: clear states (scheduled/running/fired), feedback, and error handling.

---

## 2) Analysis (reasoning, ambiguities, dependencies)

### 2.1 Key ambiguities to resolve (stakeholder questions)
- **App form factor**: Is this a CLI, desktop GUI (e.g., Tkinter), web app, or mobile app?
- **Notification mechanism**: Should alarms/reminders work only while the app is running, or must they fire even if the app is closed (OS-level scheduling)?
- **Recurrence rules**:
  - Alarms: one-time vs daily/weekly; support for weekdays-only; multiple times per day?
  - Reminders: one-time only or recurring?
- **Snooze**: Required for alarms? If yes, fixed or configurable snooze duration?
- **Audio**: Should alarms play a sound, show a visual alert, or both?
- **World clock data**: Should the app ship with a fixed list of time zones (IANA), allow searching by city, or both?
- **Conversion feature depth**: Which conversions are in-scope (timezone conversion, epoch conversion, format conversion, duration arithmetic)?

### 2.2 Assumptions (to proceed without further input)
To make requirements actionable, this document assumes:
- The app runs locally on the user’s machine and works offline.
- Alarms/reminders are guaranteed to trigger **only while the app is running** (OS-level background scheduling is out-of-scope for v0.1).
- Alarms support **daily and weekday recurrence** at minimum; reminders are **one-time** by default.
- Alerts are implemented as at least a visible notification within the app; optional sound is configurable.
- Time zone support uses the IANA time zone database (e.g., `zoneinfo`) when available.

These assumptions are flagged so they can be tightened/changed later.

### 2.3 Dependencies and constraints
- Correct time zone conversion depends on access to an IANA time zone database.
- Triggering alarms/reminders depends on the system clock; handling clock changes requires additional logic.
- Persistence requires a local storage format (e.g., JSON/SQLite). JSON is simplest; SQLite scales better.

### 2.4 Edge cases to cover
- DST spring-forward gaps (non-existent local times) and fall-back overlaps (ambiguous local times).
- Alarms/reminders scheduled in a time zone different from the user’s current system time zone.
- System clock changes while timers are running.
- Multiple simultaneous triggers (two alarms at the same time).
- App restart: ensure no loss of configuration; define behavior for missed triggers.

---

## 3) Documented Requirements

Each requirement includes brief reasoning first, followed by a testable “shall” statement.

### 3.1 General & Data Model

**Rationale (General)**
- The app spans multiple time-based features; consistent identifiers, statuses, and persistence are needed to avoid inconsistent behavior.

1. **Unique Identification**
   - Reasoning: Alarms, reminders, and timers must be editable and traceable even after restart.
   - Requirement: The system shall assign each alarm and reminder a stable unique identifier that persists across application restarts.

2. **Status Model**
   - Reasoning: Users need to understand whether items will trigger and whether they already fired.
   - Requirement: The system shall represent alarms and reminders with a status at minimum including `enabled/disabled` and `scheduled/fired`.

3. **Persistence**
   - Reasoning: The user expects configured alarms/reminders and preferences to remain after closing the app.
   - Requirement: The system shall persist alarms, reminders, world clock selections, and user preferences to local storage and restore them at startup.

4. **Time Zone Representation**
   - Reasoning: World clock and conversions require explicit time zone context.
   - Requirement: The system shall store time zone information using IANA time zone identifiers (e.g., `Europe/Berlin`).

### 3.2 Alarms

**Rationale (Alarms)**
- Alarms must trigger at specified times of day and notify the user reliably while the app runs.

5. **Create Alarm**
   - Reasoning: Core need is to schedule wake-up/alert times.
   - Requirement: The system shall allow the user to create an alarm specifying a time of day and an optional label.

6. **Edit/Delete Alarm**
   - Reasoning: Users must maintain their schedule.
   - Requirement: The system shall allow the user to edit and delete existing alarms.

7. **Enable/Disable Alarm**
   - Reasoning: Temporarily turning off alarms is common.
   - Requirement: The system shall allow the user to enable or disable an alarm without deleting it.

8. **Alarm Recurrence**
   - Reasoning: Repeating alarms are expected for daily routines.
   - Requirement: The system shall support at minimum the following alarm recurrence options: one-time, daily, and weekdays (Mon–Fri).

9. **Alarm Trigger & Notification**
   - Reasoning: A scheduled alarm is only useful if it clearly alerts the user.
   - Requirement: When an enabled alarm reaches its scheduled trigger time, the system shall present an in-app alert that includes the alarm label (if any).

10. **Simultaneous Alarm Handling**
    - Reasoning: Multiple alarms may trigger at the same minute.
    - Requirement: If multiple alarms trigger at the same time, the system shall present an alert for each triggered alarm.

11. **Snooze (Optional / Configurable Scope)**
    - Reasoning: Snooze is common but was not explicitly requested; including it may affect UX and scheduling logic.
    - Requirement: If snooze is implemented, the system shall allow the user to postpone a triggered alarm by a configurable snooze duration.

### 3.3 Reminders (Specific Date & Time)

**Rationale (Reminders)**
- Reminders differ from alarms by being tied to a specific calendar date and time.

12. **Create Reminder**
    - Reasoning: Users need reminders at specific date+time.
    - Requirement: The system shall allow the user to create a reminder specifying a date, a time, an optional time zone, and an optional message.

13. **Edit/Delete/Enable/Disable Reminder**
    - Reasoning: Users must manage reminders similarly to alarms.
    - Requirement: The system shall allow the user to edit, delete, enable, and disable reminders.

14. **Reminder Trigger & Notification**
    - Reasoning: Reminders must reliably notify at the scheduled instant.
    - Requirement: When an enabled reminder reaches its scheduled trigger instant, the system shall present an in-app alert that includes the reminder message (if any).

15. **Post-Trigger Behavior**
    - Reasoning: One-time reminders should not keep re-firing.
    - Requirement: After a reminder triggers, the system shall mark it as fired and shall not trigger it again unless the user edits it to a future time.

16. **Missed Reminder Policy (On Restart)**
    - Reasoning: If the app was closed at trigger time, behavior must be defined.
    - Requirement: On startup, the system shall detect enabled reminders scheduled in the past and shall mark them as missed without triggering an alert.

### 3.4 Countdown Timer

**Rationale (Countdown)**
- Users need a timer for durations that can be controlled and that alerts on completion.

17. **Set Countdown Duration**
    - Reasoning: Countdown timers start from a user-defined duration.
    - Requirement: The system shall allow the user to configure a countdown duration in hours, minutes, and seconds.

18. **Start/Pause/Resume/Cancel**
    - Reasoning: Users commonly interrupt timers.
    - Requirement: The system shall allow the user to start, pause, resume, and cancel a countdown timer.

19. **Countdown Completion Alert**
    - Reasoning: The user needs to know when time is up.
    - Requirement: When the countdown reaches zero, the system shall present an in-app completion alert.

20. **Timer Accuracy**
    - Reasoning: Counting should be robust even if the UI lags.
    - Requirement: The system shall compute remaining countdown time based on monotonic time measurement when available, rather than relying solely on periodic UI updates.

### 3.5 Pomodoro Timer

**Rationale (Pomodoro)**
- Pomodoro requires structured work/break intervals and a clear cycle state.

21. **Pomodoro Configuration**
    - Reasoning: Different users use different durations.
    - Requirement: The system shall allow the user to configure pomodoro work duration, short break duration, long break duration, and the number of work sessions per cycle before a long break.

22. **Pomodoro Session Control**
    - Reasoning: Users need to start/stop and handle interruptions.
    - Requirement: The system shall allow the user to start, pause, resume, and stop the pomodoro timer.

23. **Pomodoro Phase Transitions**
    - Reasoning: The timer must switch phases predictably.
    - Requirement: The system shall automatically transition between work and break phases according to the configured cycle rules.

24. **Pomodoro Alerts**
    - Reasoning: Users need a clear signal when a phase ends.
    - Requirement: The system shall present an in-app alert at the end of each pomodoro phase (work or break) indicating the next phase.

### 3.6 World Clock

**Rationale (World clock)**
- Users want to compare current times across multiple locations.

25. **Add/Remove Time Zones**
    - Reasoning: Users need a personalized list.
    - Requirement: The system shall allow the user to add and remove time zones from a world clock list.

26. **Display Current Time**
    - Reasoning: World clock’s primary output is “now” in each zone.
    - Requirement: The system shall display the current date and time for each selected time zone.

27. **DST Awareness**
    - Reasoning: Correct “now” depends on DST rules.
    - Requirement: The system shall compute world clock times using the selected time zone’s DST rules when applicable.

### 3.7 Date & Time Conversions

**Rationale (Conversions)**
- Conversions are explicitly requested but the depth is ambiguous; define a minimal, testable core.

28. **Time Zone Conversion**
    - Reasoning: Common conversion is between two zones for a given instant.
    - Requirement: The system shall convert a user-specified date+time from a source time zone to a target time zone and display the result.

29. **UTC Conversion**
    - Reasoning: UTC is a standard reference.
    - Requirement: The system shall allow converting a local date+time in a specified time zone to UTC.

30. **Epoch Conversion (Optional / Configurable Scope)**
    - Reasoning: Unix epoch conversion is frequently useful but may be beyond minimal scope.
    - Requirement: If epoch conversion is implemented, the system shall convert between Unix epoch seconds and a date+time in a specified time zone.

31. **Formatting Options**
    - Reasoning: Users may need a specific display format.
    - Requirement: The system shall support displaying converted results in both 24-hour and 12-hour formats.

### 3.8 Time Handling & Correctness

**Rationale (Correctness)**
- Time is notoriously tricky; correctness requirements reduce user-visible surprises.

32. **Ambiguous/Non-existent Local Times**
    - Reasoning: DST transitions can create invalid or ambiguous local times.
    - Requirement: When a user inputs a local date+time that is ambiguous or non-existent due to a DST transition, the system shall detect this and require the user to choose a resolution (e.g., earlier vs later offset) or adjust to the nearest valid time.

33. **Clock Change Resilience**
    - Reasoning: System clock changes should not break running timers.
    - Requirement: The system shall base countdown and pomodoro timing on a monotonic clock when available, so that manual system clock changes do not cause large jumps in remaining time.

34. **Time Zone Change Behavior (Assumption-based)**
    - Reasoning: Users may travel; scheduled items need a defined policy.
    - Requirement: The system shall treat alarms as “time-of-day in the user’s current local time zone” and reminders as “a specific instant in their configured time zone,” unless the user explicitly changes the item’s time zone.

### 3.9 Usability & Accessibility

**Rationale (Usability)**
- Users must be able to understand and control timers quickly.

35. **Input Validation**
    - Reasoning: Date/time inputs can be invalid.
    - Requirement: The system shall validate user inputs for dates, times, durations, and time zones and shall present a clear error message when inputs are invalid.

36. **Clear State Display**
    - Reasoning: Users need feedback for scheduled and running items.
    - Requirement: The system shall display the next trigger time for each enabled alarm and each enabled reminder.

### 3.10 Non-Functional Requirements

**Rationale (NFRs)**
- Local timer apps are expected to be responsive, private, and reliable.

37. **Offline Operation**
    - Reasoning: Alarm/timer should not depend on network.
    - Requirement: The system shall function without network connectivity.

38. **Local Privacy**
    - Reasoning: Reminders can contain personal text.
    - Requirement: The system shall store all user data locally and shall not transmit reminder or alarm data over the network.

39. **Startup Time**
    - Reasoning: Users open timer apps for quick actions.
    - Requirement: The system shall restore persisted data and become usable within 2 seconds on a typical modern laptop under normal load.

---

## 4) Traceability (Need → Requirement mapping)
- Needs 1–3 → Requirements 5–11
- Needs 4–5 → Requirements 12–16
- Need 6 → Requirements 17–20
- Need 7 → Requirements 21–24
- Need 8 → Requirements 25–27
- Need 9 → Requirements 28–31
- Needs 10–12 → Requirements 1–4, 32–39

---

## 5) Open Questions (to finalize v1.0 requirements)
1. Should alarms/reminders trigger when the app is not running (OS scheduling)?
2. Are recurring reminders required (weekly/monthly), and what recurrence rules are needed?
3. Is snooze mandatory, and should it apply to reminders as well?
4. What UI is intended for this project (CLI vs GUI), and what platform(s) must be supported?
5. Which date/time conversion modes are required beyond timezone + format (epoch, duration arithmetic, calendar conversions)?
