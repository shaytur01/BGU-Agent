from icalendar import Calendar
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

ICS_FILE = Path(__file__).parent.parent / "data" / "moodle_calendar.ics"


def load_deadlines():
    """Reads the .ics file and returns a list of all assignments with their due dates"""
    with open(ICS_FILE, "rb") as f:
        cal = Calendar.from_ical(f.read())

    deadlines = []
    for component in cal.walk():
        # Each assignment is a VEVENT component
        if component.name == "VEVENT":
            summary = str(component.get("SUMMARY", ""))
            dtstart = component.get("DTSTART")

            if dtstart:
                due_date = dtstart.dt
                # .ics dates can be datetime or just date — normalize to date
                if isinstance(due_date, datetime):
                    due_date = due_date.date()

                deadlines.append({
                    "title": summary,
                    "due_date": due_date
                })

    # Sort by due date — closest first
    deadlines.sort(key=lambda d: d["due_date"])
    return deadlines


def get_upcoming_deadlines(days_ahead=7):
    """Returns deadlines due within the next X days"""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    all_deadlines = load_deadlines()
    return [d for d in all_deadlines if today <= d["due_date"] <= cutoff]


def get_tomorrow_deadlines():
    """Returns deadlines due exactly tomorrow"""
    tomorrow = date.today() + timedelta(days=1)
    all_deadlines = load_deadlines()
    return [d for d in all_deadlines if d["due_date"] == tomorrow]


def format_deadline(deadline):
    """Formats a deadline as a readable message"""
    today = date.today()
    days_left = (deadline["due_date"] - today).days

    if days_left == 0:
        urgency = "⚠️ היום!"
    elif days_left == 1:
        urgency = "⏰ מחר!"
    else:
        urgency = f"📅 בעוד {days_left} ימים"

    return (
        f"📌 {deadline['title']}\n"
        f"{urgency} — {deadline['due_date'].strftime('%d/%m/%Y')}"
    )
