import os
import requests
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

LOGIN_URL = "https://portal.bgu.ac.il/Portal/Account/StandardLogin"
ASSIGNMENTS_URL = "https://portal.bgu.ac.il/Portal/StudentExamsAndTasksListViewBlockList/SearchExamsAndTasks"

# Maps API course names → display names. Add more as needed.
COURSE_NAMES = {
    "Analysis and Design of Software Systems S2": "ניתוח ועיצוב מערכות תוכנה",
    "פיסיקה מודרנית לתלמידי הנדסת תוכנה 2026": "פיסיקה מודרנית לתלמידי הנדסת תוכנה",
}


def translate_course(name: str) -> str:
    name = name.strip()
    return COURSE_NAMES.get(name, name)


def get_session():
    """Logs into BGU portal and returns an authenticated session with JWT token"""
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Referer": "https://portal.bgu.ac.il/Portal/Account/Login",
        "Origin": "https://portal.bgu.ac.il"
    })

    login_response = session.post(LOGIN_URL, json={
        "username": os.getenv("BGU_USERNAME"),
        "password": os.getenv("BGU_PASSWORD"),
        "id": os.getenv("BGU_ID"),
        "cultureCode": "he-IL"
    })

    # Extract JWT token and add to all future requests as Authorization header
    data = login_response.json()
    token = data.get("token", "")
    session.headers.update({"Authorization": f"Bearer {token}"})

    return session


def fetch_assignments():
    """Logs in and fetches all assignments for the current semester"""
    session = get_session()

    # Date range: start of this academic year to end of semester
    payload = {
        "cultureCode": "he-IL",
        "dataTypes": [1, 2, 3],
        "fromDate": "2025-10-01T00:00:00.000Z",
        "searchOneDay": False,
        "showWarningBubblePeriod": 6,
        "term": None,
        "toDate": "2026-09-30T00:00:00.000Z"
    }

    response = session.post(ASSIGNMENTS_URL, json=payload)
    return response.json()


def get_upcoming_assignments(days_ahead=7):
    """Returns assignments due within the next X days"""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)

    all_assignments = fetch_assignments()
    upcoming = []

    for item in all_assignments:
        raw_date = item.get("date", "")
        title = item.get("name", "")
        if not raw_date or not title or title.lower() == "none":
            continue

        # Parse the date from "2026-04-21T18:59:00Z" format
        due_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()

        if today <= due_date <= cutoff:
            upcoming.append({
                "title": title,
                "course": translate_course(item.get("courseName", "")),
                "due_date": due_date,
                "link": item.get("linkUrl", "")
            })

    upcoming.sort(key=lambda x: x["due_date"])
    return upcoming


EXAM_KEYWORDS = ["exam", "מבחן", "בחינה", "בחן", "test", "midterm", "final", "quiz"]

def is_exam(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in EXAM_KEYWORDS)


def get_upcoming_exams(days_ahead=60):
    """Returns exam-type items due within the next X days"""
    today = date.today()
    cutoff = today + timedelta(days=days_ahead)
    all_items = fetch_assignments()
    exams = []

    for item in all_items:
        raw_date = item.get("date", "")
        title = item.get("name", "")
        if not raw_date or not title or title.lower() == "none":
            continue
        if not is_exam(title):
            continue
        due_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).date()
        if today <= due_date <= cutoff:
            exams.append({
                "title": title,
                "course": translate_course(item.get("courseName", "")),
                "due_date": due_date,
            })

    exams.sort(key=lambda x: x["due_date"])
    return exams


def format_exams(exams):
    if not exams:
        return "אין מבחנים קרובים 🎉"
    lines = []
    today = date.today()
    for e in exams:
        days_left = (e["due_date"] - today).days
        urgency = "⚠️ היום" if days_left == 0 else f"בעוד {days_left} ימים"
        due_str = e["due_date"].strftime("%d/%m/%Y")
        lines.append(f"━━━━━━━━━━━━━━━━━━")
        lines.append(f"📚 {e['course']}")
        lines.append(f"📌 {e['title']}")
        lines.append(f"🗓 {due_str}  •  {urgency}\n")
    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def get_tomorrow_assignments():
    """Returns assignments due exactly tomorrow"""
    tomorrow = date.today() + timedelta(days=1)
    all_upcoming = get_upcoming_assignments(days_ahead=2)
    return [a for a in all_upcoming if a["due_date"] == tomorrow]


def format_assignment(assignment):
    today = date.today()
    days_left = (assignment["due_date"] - today).days
    if days_left == 0:
        urgency = "⚠️ היום"
    elif days_left == 1:
        urgency = "⏰ מחר"
    else:
        urgency = f"בעוד {days_left} ימים"
    due_str = assignment["due_date"].strftime("%d/%m/%Y")
    return f"  📌 {assignment['title']}\n  🗓 {due_str}  •  {urgency}"


def format_assignments_grouped(assignments):
    """Groups assignments by course and formats as a clean organized message"""
    if not assignments:
        return "אין הגשות קרובות 🎉"

    # Group by course name
    by_course = {}
    for a in assignments:
        course = a["course"]
        by_course.setdefault(course, []).append(a)

    lines = []
    for course, items in by_course.items():
        lines.append(f"━━━━━━━━━━━━━━━━━━")
        lines.append(f"📚 {course}\n")
        for item in items:
            lines.append(format_assignment(item))
            lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


    return message
