import json
from datetime import datetime
from pathlib import Path

SCHEDULE_FILE = Path(__file__).parent.parent / "data" / "schedule.json"

DAY_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday"
}

DAY_HEBREW = {
    "sunday": "יום ראשון",
    "monday": "יום שני",
    "tuesday": "יום שלישי",
    "wednesday": "יום רביעי",
    "thursday": "יום חמישי",
    "friday": "יום שישי",
    "saturday": "יום שבת",
    "today": "היום"
}


def load_schedule():
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["schedule"]


def get_today_classes():
    today = DAY_MAP[datetime.now().weekday()]
    classes = load_schedule()
    todays = [c for c in classes if c["day"].lower() == today]
    todays.sort(key=lambda c: c["start"])
    return todays


def get_tomorrow_classes():
    tomorrow_index = (datetime.now().weekday() + 1) % 7
    tomorrow = DAY_MAP[tomorrow_index]
    classes = load_schedule()
    tomorrows = [c for c in classes if c["day"].lower() == tomorrow]
    tomorrows.sort(key=lambda c: c["start"])
    return tomorrows, tomorrow


def get_classes_by_day(day: str):
    classes = load_schedule()
    result = [c for c in classes if c["day"].lower() == day.lower()]
    result.sort(key=lambda c: c["start"])
    return result


def get_next_class():
    now = datetime.now()
    today = DAY_MAP[now.weekday()]
    current_time = now.strftime("%H:%M")

    classes = load_schedule()

    # Look for next class today (not yet started)
    todays = sorted(
        [c for c in classes if c["day"].lower() == today and c["start"] > current_time],
        key=lambda c: c["start"]
    )

    if todays:
        return todays[0], "today"

    # Look in the next 6 days
    for days_ahead in range(1, 7):
        next_day_index = (now.weekday() + days_ahead) % 7
        next_day = DAY_MAP[next_day_index]
        next_classes = sorted(
            [c for c in classes if c["day"].lower() == next_day],
            key=lambda c: c["start"]
        )
        if next_classes:
            return next_classes[0], next_day

    return None, None


def format_class(cls):
    location = f"בניין {cls['building']}, חדר {cls['room']}" if cls["building"] != "online" else "אונליין"
    # \u200f is the Unicode Right-to-Left Mark — forces correct RTL display for lines with numbers
    rtl = "\u200f"
    return (
        f"📚 {cls['course']}\n"
        f"🕐 {rtl}{cls['end']} - {cls['start']}\n"
        f"📍 {rtl}{location}\n"
        f"📝 {cls['type']}"
    )
