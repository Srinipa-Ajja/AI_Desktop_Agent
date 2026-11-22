# Gemini + HCU Terminal Chat Agent

A simple terminal chat interface that lets you talk to a Gemini agent which can see and control your Linux desktop using Hybrid Computer Use (HCU).

## Quick Start

### 1. Get a Gemini API Key

1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**
2. Click **"Create API key"**
3. Copy the key (it starts with `AIza...`)

### 2. Run the agent

```bash
cd ~/Hybrid-Computer-Use

# Option A — set key in env (recommended)
export GEMINI_API_KEY="AIzaSy..."
python3 chat_agent.py

# Option B — it will prompt you
python3 chat_agent.py

# Option C — inline
GEMINI_API_KEY="AIzaSy..." python3 chat_agent.py
```

### 3. Talk to it!

```
[You] What windows are currently open?
[You] Take a screenshot and describe the screen
[You] Open the terminal app
[You] Click the Save button in LibreOffice Writer
```

---

## Options

| Flag | Default | Description |
|---|---|---|
| `--model` | `gemini-3.8-flash` | Gemini model to use |
| `--verbose` | off | Print full tool arguments |
| `--max-turns` | 15 | Max tool-call turns per task |

```bash
python3 chat_agent.py --model gemini-3.8-flash --verbose
```

## How It Works

```
You (terminal)
    │
    ▼
chat_agent.py  ◄──► Google Gemini API (via GEMINI_API_KEY)
    │
    ▼
artifacts/computer-use  (HCU binary)
    │
    ├── AX tool  → AT-SPI2 accessibility tree (reads/clicks UI controls)
    └── GUI tool → X11 screenshot + mouse/keyboard input
```

The Gemini model decides which tool to call. HCU executes it on your live desktop and returns results (including screenshots) back to the model.

## Requirements

- Python 3.8+
- `pip install google-genai pillow` (auto-installed on first run)
- `artifacts/computer-use` binary (already built in this repo)
- A live desktop session (X11/GNOME) — run from the desktop terminal, not SSH

## Troubleshooting

| Problem | Fix |
|---|---|
| `runtime_error: missing DBUS_SESSION_BUS_ADDRESS` | Run from a desktop terminal, not SSH. The agent needs a live GUI session. |
| `404 NOT_FOUND: model not available` | Use `--model gemini-3.8-flash` (the default) |
| `ClientError: 401 UNAUTHENTICATED` | Your API key is invalid. Get one from [AI Studio](https://aistudio.google.com/app/apikey) — it starts with `AIza...` |
| Tools time out | Desktop session may be locked or slow. Try a simpler task first. |
