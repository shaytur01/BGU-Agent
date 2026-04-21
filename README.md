# BGU Student AI Agent

A personal AI agent for daily student life at Ben-Gurion University of the Negev.
Built with a **multi-model AI pipeline**: Claude Haiku for intent classification, Groq Whisper for Hebrew speech-to-text, and Gemini 2.5 Flash for PDF summarization — all connected to a reverse-engineered university portal API.

---

## Architecture

```
User input (text / voice / PDF)
            │
            ├── Voice ──► [Groq Whisper-large-v3] ── Hebrew STT ──► text
            │
            ├── PDF ───► [Google Gemini 2.5 Flash] ─ PDF summary ──► summary PDF
            │
            └── Text ──► [Anthropic Claude Haiku] ── intent (1 token) ──► handler
                                                                               │
                                                            ┌──────────────────┤
                                                            │                  │
                                                    [BGU Portal API]   [schedule.json]
                                                    JWT auth + REST    local timetable
                                                            │
                                                            ▼
                                                    [Telegram Bot]
                                                    formatted Hebrew reply
```

**Design decision:** Claude classifies intent into a single keyword (`next_class`, `today_classes`, `deadlines`, `specific_day:monday`, etc.) using `max_tokens=10`. All formatting is handled by Python — the LLM never writes the reply. This keeps latency <300ms and output 100% deterministic.

---

## AI Models Used

| Model | Provider | Role |
|---|---|---|
| **Claude Haiku** (`claude-haiku-4-5`) | Anthropic | Natural language intent classification |
| **Whisper Large v3** | Groq | Hebrew voice-to-text transcription |
| **Gemini 2.5 Flash** | Google | Multimodal PDF lecture summarization |

---

## Features

### Natural Language Understanding
- Ask in Hebrew — the agent understands intent and routes to the right handler
- Examples: *"מה השיעור הבא שלי?"*, *"מה יש לי ביום שלישי?"*, *"מה ההגשות הקרובות?"*

### Voice Messages
- Send a voice note in Hebrew — transcribed by Groq Whisper and handled as text

### PDF Lecture Summarizer
- Send any lecture PDF — Gemini reads it natively and returns a structured Hebrew summary as a PDF
- Output includes: main topics, detailed summary, key concepts with explanations

### Live Class Schedule
- Next upcoming class
- Today's / tomorrow's classes
- Classes for any specific day of the week

### Assignment Deadlines
- Fetches upcoming assignments from the BGU portal via authenticated REST API (JWT)
- Assignments grouped by course with days-remaining urgency indicators

### Israeli Holiday Calendar
- Integrates the `holidays` package for Israeli public holidays
- Extended with manually maintained dates: ערב פסח, חול המועד, יום הזיכרון, ערב שבועות
- Solemn days (יום הזיכרון, יום כיפור) get a respectful 🕯️ message; festive days get 🎉
- All schedule queries and reminders are suppressed on holidays

### Automated Notifications (via APScheduler)
| Time | Job |
|---|---|
| 08:00 daily | Today's class summary + rain alert if needed |
| 30 min before class | Class reminder (skipped on holidays) |
| 20:00 daily | Reminder for tomorrow's assignment deadlines |
| Every 2 hours | Check BGU portal for newly added assignments |

### Weather Alerts
- Fetches Beer Sheva forecast from Open-Meteo (free, no API key)
- Alerts if rain is expected tomorrow (WMO code ≥ 51 or precipitation > 0.5mm)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | python-telegram-bot v22 |
| Intent classification | Anthropic Claude Haiku |
| Voice transcription | Groq Whisper-large-v3 |
| PDF summarization | Google Gemini 2.5 Flash |
| Hebrew PDF generation | fpdf2 + python-bidi + Arial Unicode |
| University portal | Reverse-engineered BGU REST API (JWT auth) |
| Holiday calendar | `holidays` package + custom Israeli dates |
| Weather | Open-Meteo API |
| Scheduling | APScheduler via Telegram JobQueue |
| Language | Python 3.12 |

---

## Setup

**1. Clone and create a virtual environment**
```bash
git clone https://github.com/shaytur01/BGU-Agent.git
cd BGU-Agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables**
```bash
cp .env.example .env
# Fill in your keys
```

Required keys:
| Key | Source |
|---|---|
| `TELEGRAM_TOKEN` | [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) (free tier available) |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) |
| `BGU_USERNAME` / `BGU_PASSWORD` / `BGU_ID` | BGU portal credentials |

**3. Add your schedule**

Edit `data/schedule.json` with your weekly timetable:
```json
{
  "schedule": [
    {
      "day": "monday",
      "course": "Course Name",
      "type": "שעור",
      "start": "09:00",
      "end": "11:00",
      "building": "32",
      "room": "101"
    }
  ]
}
```

**4. Run**
```bash
python main.py
```

Send `/start` to your bot on Telegram to activate all scheduled notifications.

---

## Project Structure

```
bgu-agent/
├── main.py                  # Bot entry point, all message handlers
├── modules/
│   ├── schedule.py          # Schedule parsing and query logic
│   ├── bgu_portal.py        # BGU portal JWT auth + assignments API
│   ├── pdf_summary.py       # Gemini PDF summarization + Hebrew PDF generation
│   └── weather.py           # Open-Meteo weather forecast
├── scheduler/
│   └── jobs.py              # Automated notification jobs + holiday calendar
├── data/
│   ├── schedule.json        # Weekly class schedule
│   └── seen_assignments.json  # Tracks known assignments for new-assignment alerts
├── .env.example
└── requirements.txt
```

---

## Commands

| Command | Description |
|---|---|
| `/start` | Initialize bot and activate all scheduled notifications |
| `/today` | Show today's classes |
| `/next` | Show next upcoming class |
| `/deadlines` | Show assignments due this week |
| `/help` | Full command reference |

Natural language and voice messages work for all of the above — no slash commands needed.
