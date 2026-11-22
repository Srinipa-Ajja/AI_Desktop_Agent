# Web-Based AI Desktop Assistant (Gemini + HCU)

A modern, responsive web application for interacting with an autonomous AI desktop assistant powered by **Google Gemini** and **Hybrid Computer Use (HCU)**.

---

## 🌟 Overview

This project converts the terminal chatbot into a full-featured web-based AI assistant. The web interface directly integrates with the real HCU daemon and Gemini models to control your Linux desktop (X11 & AT-SPI2).

### Key Features
- **Modern Chat Interface**: Dark-navy & blue UI (`#0b0f19`, `#101726`, `#2e4990`, `#9cadd4`), responsive layout for desktop, laptop, and mobile.
- **Real-Time Desktop Task Tracking**: Live status indicator displaying:
  - *Ready*
  - *Understanding request*
  - *Executing desktop task*
  - *Waiting for tool result*
  - *Task completed / Task failed*
- **Action & Screenshot Inspection**: Expandable tool execution cards showing tool names (`hcu_ax`, `hcu_gui`, `run_shell`), action arguments, output logs, and in-chat screenshot previews with zoom.
- **Task Cancellation**: Cancel running desktop tasks at any point using the Stop button.
- **Conversation History**: Create, switch, and delete multiple chat sessions with persistent context.
- **Desktop Concurrency Safeguards**: Thread-safe desktop execution lock prevents concurrent tasks from interfering with mouse/keyboard/window operations.
- **Dual Support**: Use the web interface or continue using the terminal CLI (`chat_agent.py`).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Browser (Web UI)                      │
│      React 18 + Vite (http://localhost:5173 or port 8000)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ SSE / REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Port 8000)               │
│                  backend/app.py & desktop_agent_core.py      │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
               ▼                              ▼
      Google Gemini API            artifacts/computer-use
   (gemini-3.1-flash-lite,         (HCU Daemon Socket)
    gemini-3.5-flash-lite,                    │
    gemini-3.8-flash)            ┌────────────┴────────────┐
                                 ▼                         ▼
                              hcu_ax                    hcu_gui
                          (AT-SPI2 Linux           (X11 Screenshots,
                        Accessibility Tree)        Mouse & Keyboard)
```

---

## 🚀 Quick Start

### 1. Unified Launch (Recommended)
Launch both the backend and frontend development server with a single command:

```bash
./start_web.sh
```

Then open your browser at:
- **Web Interface:** [http://localhost:5173](http://localhost:5173) (Vite dev) or [http://127.0.0.1:8000](http://127.0.0.1:8000) (Production SPA)
- **API Health:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

Press `Ctrl+C` in the terminal to stop both servers cleanly.

---

### 2. Manual / Separate Startup

#### Step A: Start the Backend
```bash
./start_backend.sh
```
Or directly:
```bash
PYTHONPATH=.site_packages:sdk/python:$PYTHONPATH python3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

#### Step B: Start the Frontend (Vite)
In another terminal:
```bash
./start_frontend.sh
```
Or:
```bash
cd frontend && npm run dev
```

---

### 3. Terminal Interface (Still Available)
The original terminal chatbot continues to work:
```bash
PYTHONPATH=.site_packages:sdk/python python3 chat_agent.py
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | Reports backend, desktop session (AT-SPI2/X11), and Gemini API status. |
| `/api/conversations` | `GET` | Lists all chat conversations. |
| `/api/conversations` | `POST` | Creates a new conversation. |
| `/api/conversations/{id}` | `GET` | Fetches conversation messages and metadata. |
| `/api/conversations/{id}` | `DELETE` | Deletes conversation and frees agent session. |
| `/api/chat` | `POST` | Synchronous chat endpoint. Submits prompt and waits for response. |
| `/api/chat/stream` | `POST` | Server-Sent Events (SSE) streaming endpoint. Emits live `status`, `tool_call`, `tool_result`, and `final_response`. |
| `/api/tasks/{task_id}` | `GET` | Retrieves status and progress of an active desktop task. |
| `/api/tasks/{task_id}/cancel` | `POST` | Cancels an ongoing desktop operation. |
| `/api/screenshots/{filename}`| `GET` | Serves screenshots captured during task execution for browser display. |

---

## 🛡️ Security & Reliability

- **API Key Security**: The Gemini API key is loaded only on the backend (from environment variable `GEMINI_API_KEY`, `.env`, or `~/api_google`). It is never transmitted or exposed to the client browser.
- **Local Isolation**: Backend restricts CORS to local development origins (`localhost` / `127.0.0.1`).
- **Physical Desktop Lock**: A concurrency lock (`threading.Lock`) protects the desktop session so concurrent requests cannot corrupt mouse or keyboard state.
