# BGU Student AI Agent

A personal AI agent for daily student life at Ben-Gurion University. Built with a multi-model pipeline: **Claude Haiku** for natural language intent classification and **Groq Whisper-large-v3** for Hebrew voice transcription, connected to a real university portal API.

## Architecture

```
User message (text or voice)
        │
        ▼
[Groq Whisper-large-v3]  ← voice only, transcribes Hebrew audio
        │
        ▼
[Claude Haiku]  ← classifies intent into one of 10 categories (max_tokens=10)
        │
        ▼
[Python handler]  ← fetches data from BGU portal / schedule JSON
        │
        ▼
[Telegram Bot]  ← sends formatted Hebrew response
```

The intent classifier returns a single keyword (`next_class`, `today_classes`, `tomorrow_classes`, `deadlines`, `specific_day:monday`, etc.). Formatting is handled entirely by Python — Claude is never asked to write the reply, keeping latency low and output deterministic.

## Features

- **Natural language queries** — ask in Hebrew, the agent understands intent
- **Voice message support** — send a voice note, get a text reply
- **Live class schedule** — next class, today's classes, tomorrow's, or any specific day
- **Assignment deadlines** — fetches from BGU portal via authenticated JSON API (JWT)
- **Automated notifications**
  - 08:00 daily summary of the day's classes
  - 30-minute reminder before each class
  - 20:00 reminder the night before an assignment deadline

## Tech Stack

| Component | Technology |
|---|---|
| Bot framework | python-telegram-bot v22 |
| Intent classification | Anthropic Claude Haiku |
| Voice transcription | Groq Whisper-large-v3 |
| University portal | Reverse-engineered BGU REST API (JWT auth) |
| Scheduling | APScheduler via Telegram JobQueue |
| Language | Python 3.12 |

## Setup

**1. Clone and create a virtual environment**
```bash
git clone https://github.com/your-username/bgu-agent.git
cd bgu-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment variables**
```bash
cp .env.example .env
# Fill in your keys in .env
```

You need:
- Telegram bot token — from [@BotFather](https://t.me/BotFather)
- Anthropic API key — from [console.anthropic.com](https://console.anthropic.com)
- Groq API key — from [console.groq.com](https://console.groq.com) (free)
- BGU portal credentials (username, password, student ID)

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

Send `/start` to your bot on Telegram to activate scheduled notifications.

## Project Structure

```
bgu-agent/
├── main.py                  # Bot entry point, all message handlers
├── modules/
│   ├── schedule.py          # Schedule parsing and query logic
│   └── bgu_portal.py        # BGU portal authentication + assignments API
├── scheduler/
│   └── jobs.py              # Automated notification jobs
├── data/
│   └── schedule.json        # Weekly class schedule
├── .env.example
└── requirements.txt
```
