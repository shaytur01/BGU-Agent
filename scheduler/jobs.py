import json
from datetime import datetime, timedelta, timezone, time, date
from pathlib import Path
import holidays
from modules.schedule import get_today_classes, format_class
from modules.bgu_portal import get_upcoming_assignments, get_tomorrow_assignments, format_assignments_grouped
from modules.weather import get_tomorrow_weather, rain_expected, format_weather_alert

israel_holidays = holidays.Israel(years=range(2025, 2028))

EXTRA_HOLIDAYS = {
    date(2026, 4, 1): "ערב פסח",
    date(2026, 4, 3): "חול המועד פסח",
    date(2026, 4, 4): "חול המועד פסח",
    date(2026, 4, 5): "חול המועד פסח",
    date(2026, 4, 6): "חול המועד פסח",
    date(2026, 4, 7): "חול המועד פסח",
    date(2026, 4, 21): "יום הזיכרון",
    date(2026, 5, 21): "ערב שבועות",
    date(2025, 4, 13): "ערב פסח",
    date(2025, 4, 15): "חול המועד פסח",
    date(2025, 4, 16): "חול המועד פסח",
    date(2025, 4, 17): "חול המועד פסח",
    date(2025, 4, 18): "חול המועד פסח",
    date(2025, 4, 22): "יום הזיכרון",
    date(2025, 6, 1): "ערב שבועות",
}

SOLEMN_DAYS = {"יום הזיכרון", "יום כיפור"}
ISRAEL_TZ = timezone(timedelta(hours=3))
notified_today = set()

SEEN_ASSIGNMENTS_FILE = Path(__file__).parent.parent / "data" / "seen_assignments.json"


def get_holiday(d: date) -> str | None:
    return israel_holidays.get(d) or EXTRA_HOLIDAYS.get(d)


def is_solemn(holiday_name: str) -> bool:
    return any(s in holiday_name for s in SOLEMN_DAYS)


def load_seen_assignments() -> set:
    if SEEN_ASSIGNMENTS_FILE.exists():
        return set(json.loads(SEEN_ASSIGNMENTS_FILE.read_text()))
    return set()


def save_seen_assignments(seen: set):
    SEEN_ASSIGNMENTS_FILE.write_text(json.dumps(list(seen)))


async def send_daily_summary(context):
    """Runs at 8:00 AM every day — sends today's classes and tomorrow's weather"""
    global notified_today
    notified_today = set()

    chat_id = context.job.data
    today = date.today()
    classes = get_today_classes()

    holiday_name = get_holiday(today)
    if holiday_name:
        solemn = is_solemn(holiday_name)
        greeting = "בוקר טוב." if solemn else "☀️ בוקר טוב!"
        wish = "יום זיכרון מכובד 🕯️" if solemn else "חג שמח! 🎉"
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{greeting} היום {holiday_name}\n\nאין שיעורים. {wish}"
        )
        return

    if not classes:
        message = "☀️ בוקר טוב! אין שיעורים היום 🎉"
    else:
        message = "☀️ בוקר טוב! השיעורים שלך היום:\n\n"
        for cls in classes:
            message += format_class(cls) + "\n\n"

    # Add weather alert if rain expected tomorrow
    weather = get_tomorrow_weather()
    if rain_expected(weather):
        message += "\n━━━━━━━━━━━━━━━━━━\n" + format_weather_alert(weather)

    await context.bot.send_message(chat_id=chat_id, text=message)


async def check_upcoming_classes(context):
    """Runs every minute — checks if a class starts in 30 minutes"""
    if get_holiday(date.today()):
        return

    chat_id = context.job.data
    now = datetime.now()
    in_30_minutes = (now + timedelta(minutes=30)).strftime("%H:%M")

    for cls in get_today_classes():
        if cls["start"] == in_30_minutes and cls["start"] not in notified_today:
            notified_today.add(cls["start"])
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ תזכורת! בעוד 30 דקות יש לך שיעור:\n\n{format_class(cls)}"
            )


async def send_deadline_reminder(context):
    """Runs at 20:00 every day — reminds about tomorrow's deadlines"""
    chat_id = context.job.data
    deadlines = get_tomorrow_assignments()
    if not deadlines:
        return
    await context.bot.send_message(
        chat_id=chat_id,
        text="📚 תזכורת הגשות! מחר יש לך:\n\n" + format_assignments_grouped(deadlines)
    )


async def check_new_assignments(context):
    """Runs every 2 hours — notifies if a new assignment was added to the portal"""
    chat_id = context.job.data
    seen = load_seen_assignments()

    all_assignments = get_upcoming_assignments(days_ahead=60)
    current_ids = {f"{a['title']}|{a['due_date']}" for a in all_assignments}

    new_ones = [a for a in all_assignments if f"{a['title']}|{a['due_date']}" not in seen]

    if new_ones and seen:  # Only notify after the first run (seen is not empty)
        for a in new_ones:
            days_left = (a["due_date"] - date.today()).days
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🔔 הגשה חדשה נוספה!\n\n"
                    f"📚 {a['course']}\n"
                    f"📌 {a['title']}\n"
                    f"🗓 {a['due_date'].strftime('%d/%m/%Y')} (בעוד {days_left} ימים)"
                )
            )

    save_seen_assignments(current_ids)


def setup_jobs(app, chat_id):
    app.job_queue.run_daily(
        send_daily_summary,
        time=time(8, 0, tzinfo=ISRAEL_TZ),
        data=chat_id,
        name="daily_summary"
    )

    app.job_queue.run_daily(
        send_deadline_reminder,
        time=time(20, 0, tzinfo=ISRAEL_TZ),
        data=chat_id,
        name="deadline_reminder"
    )

    app.job_queue.run_repeating(
        check_upcoming_classes,
        interval=60,
        first=10,
        data=chat_id,
        name="class_reminder"
    )

    app.job_queue.run_repeating(
        check_new_assignments,
        interval=7200,  # every 2 hours
        first=30,
        data=chat_id,
        name="new_assignment_checker"
    )
