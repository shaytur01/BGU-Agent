import os
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import anthropic
from groq import Groq
from modules.pdf_summary import process_lecture_pdf

from modules.schedule import get_next_class, get_today_classes, get_tomorrow_classes, get_classes_by_day, format_class, DAY_HEBREW
from modules.bgu_portal import get_upcoming_assignments, format_assignments_grouped
from scheduler.jobs import setup_jobs

# Load secret keys from .env file
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Claude client — the AI brain
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Track if jobs are already set up (so we don't duplicate on multiple /start calls)
jobs_initialized = False


def get_schedule_context():
    """Builds a text summary of today's and next class for Claude to read"""
    next_cls, day = get_next_class()
    today_classes = get_today_classes()

    context = "המידע הזמין לך:\n"

    if today_classes:
        context += "\nשיעורי היום:\n"
        for cls in today_classes:
            context += f"- {cls['course']} ({cls['type']}) בשעה {cls['start']}-{cls['end']}, בניין {cls['building']}, חדר {cls['room']}\n"
    else:
        context += "\nאין שיעורים היום.\n"

    if next_cls:
        day_heb = DAY_HEBREW.get(day, day)
        context += f"\nהשיעור הבא: {next_cls['course']} ב{day_heb} בשעה {next_cls['start']}, בניין {next_cls['building']}, חדר {next_cls['room']}\n"

    return context


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called when user sends a PDF — summarizes it and replies with a summary PDF"""
    doc = update.message.document
    if not doc.mime_type == "application/pdf":
        await update.message.reply_text("אנא שלח קובץ PDF בלבד 📄")
        return

    await update.message.reply_text("📄 מעבד את הקובץ, זה יקח כמה שניות...")

    pdf_file = await doc.get_file()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    await pdf_file.download_to_drive(tmp_path)

    try:
        loop = asyncio.get_event_loop()
        summary_pdf_path = await loop.run_in_executor(None, process_lecture_pdf, tmp_path)
        with open(summary_pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"סיכום - {doc.file_name}",
                caption="✅ הסיכום שלך מוכן!"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ שגיאה בעיבוד הקובץ: {str(e)}")
    finally:
        os.remove(tmp_path)
        if 'summary_pdf_path' in locals():
            os.remove(summary_pdf_path)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called when user sends a voice message — transcribes and handles as text"""
    voice_file = await update.message.voice.get_file()

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    await voice_file.download_to_drive(tmp_path)

    with open(tmp_path, "rb") as audio_file:
        result = groq_client.audio.transcriptions.create(
            file=("voice.ogg", audio_file),
            model="whisper-large-v3",
            language="he"
        )
    os.remove(tmp_path)

    transcribed = result.text.strip()
    if not transcribed:
        await update.message.reply_text("לא הצלחתי להבין את ההודעה הקולית 😅")
        return

    # Feed the transcribed text into the existing natural language handler
    await handle_natural_language(update, context, override_text=transcribed)


async def handle_natural_language(update: Update, context: ContextTypes.DEFAULT_TYPE, override_text: str = None):
    """Called when user sends any text message (not a command)"""
    user_message = override_text or update.message.text

    # Step 1: Ask Claude to identify ONLY the intent — not to write the reply
    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        system="""זהה את הכוונה של המשתמש ותחזיר רק אחת מהאפשרויות הבאות, בלי שום טקסט נוסף:
next_class
today_classes
tomorrow_classes
deadlines
specific_day:sunday
specific_day:monday
specific_day:tuesday
specific_day:wednesday
specific_day:thursday
specific_day:friday
specific_day:saturday
unknown""",
        messages=[{"role": "user", "content": user_message}]
    )

    intent = response.content[0].text.strip()

    # Step 2: Our code handles formatting — not Claude
    if intent == "next_class":
        cls, day = get_next_class()
        if cls is None:
            await update.message.reply_text("לא נמצאו שיעורים קרובים 🎉")
        else:
            day_label = DAY_HEBREW.get(day, day)
            await update.message.reply_text(f"השיעור הבא שלך {day_label}:\n\n{format_class(cls)}")

    elif intent == "today_classes":
        classes = get_today_classes()
        if not classes:
            await update.message.reply_text("אין שיעורים היום 🎉")
        else:
            message = "השיעורים שלך היום:\n\n"
            for cls in classes:
                message += format_class(cls) + "\n\n"
            await update.message.reply_text(message)

    elif intent == "deadlines":
        upcoming = get_upcoming_assignments(days_ahead=7)
        await update.message.reply_text("📋 ההגשות הקרובות שלך:\n\n" + format_assignments_grouped(upcoming))

    elif intent.startswith("specific_day:"):
        # Extract the day from "specific_day:wednesday" → "wednesday"
        day = intent.split(":")[1]
        day_label = DAY_HEBREW.get(day, day)
        classes = get_classes_by_day(day)
        if not classes:
            await update.message.reply_text(f"אין שיעורים ב{day_label} 🎉")
        else:
            message = f"השיעורים שלך ב{day_label}:\n\n"
            for cls in classes:
                message += format_class(cls) + "\n\n"
            await update.message.reply_text(message)

    elif intent == "tomorrow_classes":
        classes, tomorrow = get_tomorrow_classes()
        day_label = DAY_HEBREW.get(tomorrow, tomorrow)
        if not classes:
            await update.message.reply_text(f"אין שיעורים ב{day_label} 🎉")
        else:
            message = f"השיעורים שלך ב{day_label}:\n\n"
            for cls in classes:
                message += format_class(cls) + "\n\n"
            await update.message.reply_text(message)

    else:
        await update.message.reply_text("לא הבנתי 😅 נסה לשאול על השיעור הבא, שיעורי היום, או שיעורי מחר")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global jobs_initialized
    chat_id = update.effective_chat.id

    # Save chat_id to .env so bot can auto-start next time
    env_path = Path(__file__).parent / ".env"
    env_content = env_path.read_text()
    if "TELEGRAM_CHAT_ID" not in env_content:
        with open(env_path, "a") as f:
            f.write(f"\nTELEGRAM_CHAT_ID={chat_id}")
        print(f"✅ Chat ID saved: {chat_id}")

    if not jobs_initialized:
        setup_jobs(context.application, chat_id)
        jobs_initialized = True

    await update.message.reply_text(
        "שלום! אני הסוכן שלך ב-BGU 🎓\n\n"
        "אני אשלח לך:\n"
        "• ☀️ סיכום יומי בשעה 08:00\n"
        "• ⏰ תזכורת 30 דקות לפני כל שיעור\n\n"
        "פקודות:\n"
        "/next - השיעור הבא\n"
        "/today - שיעורי היום\n"
        "/deadlines - הגשות השבוע\n\n"
        "או פשוט כתוב לי בעברית מה אתה רוצה לדעת"
    )


async def next_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cls, day = get_next_class()
    if cls is None:
        await update.message.reply_text("לא נמצאו שיעורים קרובים 🎉")
        return
    day_label = DAY_HEBREW.get(day, day)
    message = f"השיעור הבא שלך{day_label}:\n\n{format_class(cls)}"
    await update.message.reply_text(message)


async def deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upcoming = get_upcoming_assignments(days_ahead=7)
    await update.message.reply_text("📋 ההגשות הקרובות שלך:\n\n" + format_assignments_grouped(upcoming))


async def today_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    classes = get_today_classes()
    if not classes:
        await update.message.reply_text("אין שיעורים היום 🎉")
        return
    message = "השיעורים שלך היום:\n\n"
    for cls in classes:
        message += format_class(cls) + "\n\n"
    await update.message.reply_text(message)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Auto-start scheduler if chat_id already saved from a previous /start
    saved_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if saved_chat_id:
        global jobs_initialized
        setup_jobs(app, int(saved_chat_id))
        jobs_initialized = True
        print(f"✅ Scheduler auto-started for chat {saved_chat_id}")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_class))
    app.add_handler(CommandHandler("today", today_classes))
    app.add_handler(CommandHandler("deadlines", deadlines))

    # This catches ANY text message that is not a command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language))

    # This catches voice messages
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # This catches PDF files
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    async def send_startup_message(application):
        if saved_chat_id:
            await application.bot.send_message(
                chat_id=int(saved_chat_id),
                text=(
                    "שלום! אני הסוכן שלך ב-BGU 🎓\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "📬 התראות אוטומטיות:\n"
                    "• ☀️ סיכום שיעורים יומי בשעה 08:00\n"
                    "• ⏰ תזכורת 30 דקות לפני כל שיעור\n"
                    "• 📚 תזכורת הגשות בשעה 20:00 (יום לפני)\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "💬 פשוט כתוב או דבר אלי בעברית:\n"
                    "\"מה השיעור הבא שלי?\"\n"
                    "\"מה יש לי מחר?\"\n"
                    "\"מה ההגשות הקרובות?\"\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "🎙️ אפשר גם לשלוח הודעה קולית!\n\n"
                    "📄 שלח לי קובץ PDF של הרצאה\n"
                    "ואחזיר לך סיכום מסודר"
                )
            )

    app.post_init = send_startup_message

    print("Bot is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
