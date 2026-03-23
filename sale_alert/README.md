# Sale Alert

Personal tool that monitors Ticketmaster's public Discovery API for event
on-sale dates and sends you Telegram / SMS notifications so you can buy
tickets manually.

**No automated purchasing. No anti-bot bypass. Alert-only.**

## Setup

```bash
cd sale_alert
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env` and fill in your keys:
   - **TM_API_KEY** — free at https://developer.ticketmaster.com
   - **Telegram** (optional) — create a bot via @BotFather, get your chat ID
   - **Twilio** (optional) — sign up at https://twilio.com

2. Edit `config/events.yaml` with the artists you want to watch.

## Usage

```bash
# Dry mode (logs only, no real alerts sent)
python -m sale_alert.src.main --mode dry

# Live mode (sends Telegram + SMS alerts)
python -m sale_alert.src.main --mode live
```

## Docker

```bash
docker build -t sale-alert .
docker run --env-file .env sale-alert --mode dry
```

## Tests

```bash
pytest tests/ -v
```
