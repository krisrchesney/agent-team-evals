"""sched: shared calendars, reminders, free-slot search and booking for a team.

    from sched.service import Scheduler
    s = Scheduler()
    s.add_user("ann", "Ann")
    cal = s.create_calendar("Team")["id"]
    s.create_event(cal, "Standup", "2026-03-02T09:00", "30m", attendees=["ann"])
"""
