# TwitchPulse – Real-Time Twitch Chat Analyzer

Day 1 goal: stand up a production-ready foundation for a Twitch chat analysis tool that ingests thousands of live messages, processes them in real-time, and displays sleek, viewer-friendly stats on the web.

## Stack Overview

- **Backend**: FastAPI + TwitchIO + Redis + VADER sentiment analysis
- **Frontend**: Vue 3 + Vite + modern CSS (dark, Twitch-inspired theme)
- **Data Layer**: Redis (sorted sets, hashes, rolling timelines)
- **Transport**: WebSockets for live stat updates
- **Emotes**: Twitch native emotes + global & channel-specific 7TV emotes

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 18+ and npm
- Docker (for the provided Redis + backend compose setup)
- Twitch chat OAuth token with `chat:read` scope

## Quick Start

1. **Configure environment**
   ```bash
   cp env.example .env
   # edit .env with your Twitch credentials + Redis URL
   ```

2. **Start infrastructure**
   ```bash
   docker compose up -d redis
   ```

3. **Backend setup**
   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn backend.main:app --reload --port 8000
   ```

4. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev -- --host
   ```

5. Open the Vue dashboard (default `http://localhost:5173`), enter a Twitch channel, duration, and start the analysis.

### Frontend → Backend wiring

The frontend reads its API/WebSocket base URLs from Vite env variables. A production preset now lives in `frontend/.env.production`:

```
VITE_API_BASE=https://backend-wild-surf-268.fly.dev
VITE_WS_BASE=wss://backend-wild-surf-268.fly.dev
```

`npm run build` / `npm run dev --mode production` will automatically use these defaults. For other environments just override them (e.g. create `.env.local` with your own backend URL).

## Performance / Load Testing

Use the synthetic simulator to stress-test Redis + analyzer logic without hitting Twitch:

```bash
python -m backend.simulator --count 15000 --channel stress_test --duration 120
```

The script spins up a throwaway session ID filled with thousands of fake chat messages so you can connect the frontend and verify charts/metrics under load.

## Docker Workflow

Build and run backend + Redis together:

```bash
docker compose up --build
```

This exposes FastAPI on `http://localhost:8000` and Redis on `localhost:6379`.

## Environment Variables

| Variable | Description |
| --- | --- |
| `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` | Needed for Helix requests (emote metadata) |
| `TWITCH_APP_TOKEN` | Optional app access token cache |
| `TWITCH_CHAT_OAUTH_TOKEN` | **Required** user/chat token (`oauth:abcd...`) |
| `TWITCH_BOT_USERNAME` | Username associated with the chat token |
| `REDIS_URL` | Defaults to `redis://localhost:6379/0` |
| `MAX_MESSAGES`, `MAX_DURATION`, `MESSAGE_SAMPLE_RATE` | Performance tuning knobs |

## Next Steps

- Build out the FastAPI controllers, Redis integration, TwitchIO chat client, and Vue dashboard components (Stats cards, sentiment meter, top lists, etc.)

Once the pieces above are implemented, the app will provide a clean, performant window into any Twitch chat in seconds.
