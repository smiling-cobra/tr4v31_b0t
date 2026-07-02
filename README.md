# AnxietyJournal Bot

A private Telegram chatbot for daily mood check-ins and anxiety journalling. Replies empathetically via Claude, tracks streaks, and surfaces patterns over time.

## Requirements

- Python 3.11+
- MongoDB
- Telegram bot token
- Anthropic API key

## Setup

Copy `.env.example` to `.env` and fill in the values:

```
TELEGRAM_TOKEN=
CLAUDE_API_KEY=
MONGODB_URI=
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

`ANTHROPIC_MODEL` is optional. If not set, the app falls back to `claude-3-5-sonnet-latest`.

For Fly.io deployments, set or update the model with:

```bash
fly secrets set ANTHROPIC_MODEL=<your-enabled-model-id>
```

## Run

```bash
# Directly
python3 main.py

# Via Docker
docker-compose up
```

## Test

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest
```

## Docker

```bash
# Build image
docker build -t anxiety-journal-bot .

# List running containers
docker ps

# Open shell in container
docker exec -it <container_id> /bin/bash
```
