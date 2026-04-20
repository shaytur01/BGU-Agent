from datetime import datetime, timedelta, timezone, time
from modules.schedule import get_today_classes, format_class
from modules.bgu_portal import get_tomorrow_assignments, format_assignments_grouped

# Israel is UTC+3
ISRAEL_TZ = timezone(timedelta(hours=3))

# Tracks which classes we already sent a reminder for today (prevents duplicates)
notified_today = set()


async def send_daily_summary(context):
    """Runs at 8:00 AM every day — sends all today's classes"""
    global notified_today
    notified_today = set()  # Reset for the new day

    chat_id = context.job.data
    classes = get_today_classes()

    if not classes:
        await context.bot.send_message(chat_id=chat_id, text="☀️ בוקר טוב! אין שיעורים היום 🎉")
        return

    message = "☀️ בוקר טוב! השיעורים שלך היום:\n\n"
    for cls in classes:
        message += format_class(cls) + "\n\n"

    await context.bot.send_message(chat_id=chat_id, text=message)


async def check_upcoming_classes(context):
    """Runs every minute — checks if a class starts in 30 minutes"""
    chat_id = context.job.data
    now = datetime.now()
    in_30_minutes = (now + timedelta(minutes=30)).strftime("%H:%M")

    classes = get_today_classes()

    for cls in classes:
        # Check if this class starts in exactly 30 minutes and we haven't notified yet
        if cls["start"] == in_30_minutes and cls["start"] not in notified_today:
            notified_today.add(cls["start"])
            message = f"⏰ תזכורת! בעוד 30 דקות יש לך שיעור:\n\n{format_class(cls)}"
            await context.bot.send_message(chat_id=chat_id, text=message)


async def send_deadline_reminder(context):
    """Runs at 20:00 every day — reminds about tomorrow's deadlines"""
    chat_id = context.job.data
    deadlines = get_tomorrow_assignments()

    if not deadlines:
        return  # No deadlines tomorrow — stay silent

    message = "📚 תזכורת הגשות! מחר יש לך:\n\n" + format_assignments_grouped(deadlines)

    await context.bot.send_message(chat_id=chat_id, text=message)


def setup_jobs(app, chat_id):
    """Called once when user sends /start — registers all scheduled jobs"""

    # Every day at 08:00 Israel time — send daily summary
    app.job_queue.run_daily(
        send_daily_summary,
        time=time(8, 0, tzinfo=ISRAEL_TZ),
        data=chat_id,
        name="daily_summary"
    )

    # Every day at 20:00 Israel time — remind about tomorrow's deadlines
    app.job_queue.run_daily(
        send_deadline_reminder,
        time=time(20, 0, tzinfo=ISRAEL_TZ),
        data=chat_id,
        name="deadline_reminder"
    )

    # Every minute — check for upcoming classes
    app.job_queue.run_repeating(
        check_upcoming_classes,
        interval=60,  # every 60 seconds
        first=10,     # start 10 seconds after bot starts
        data=chat_id,
        name="class_reminder"
    )
