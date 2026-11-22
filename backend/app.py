"""
FastAPI Backend for Gemini + HCU AI Desktop Assistant
=====================================================
Provides REST and SSE endpoints for the web-based desktop agent chat interface.
"""

import os
import sys
import json
import time
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SITE_PACKAGES = REPO_ROOT / ".site_packages"
if SITE_PACKAGES.is_dir() and str(SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(SITE_PACKAGES))

SDK_PATH = REPO_ROOT / "sdk" / "python"
if SDK_PATH.is_dir() and str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

import desktop_agent_core as core
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Gemini + HCU Desktop Agent API",
    description="Web API for autonomous desktop assistance using Google Gemini & Hybrid Computer Use.",
    version="1.0.0",
)

# Allow local frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# State Management: Conversations & Tasks
# ---------------------------------------------------------------------------

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    tool_calls: Optional[List[Dict[str, Any]]] = None
    status: Optional[str] = None
    screenshot_url: Optional[str] = None

class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    messages: List[Message] = []

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    model: Optional[str] = None

class ActiveTask:
    def __init__(self, task_id: str, conversation_id: str):
        self.task_id = task_id
        self.conversation_id = conversation_id
        self.cancel_event = threading.Event()
        self.status = "queued"
        self.start_time = time.time()
        self.result = None
        self.error = None

# In-memory storage for active sessions, conversations, and tasks
_conversations: Dict[str, Conversation] = {}
_agent_sessions: Dict[str, core.AgentSession] = {}
_active_tasks: Dict[str, ActiveTask] = {}
_tasks_lock = threading.Lock()


def get_or_create_conversation(conv_id: Optional[str] = None) -> Conversation:
    if not conv_id or conv_id not in _conversations:
        new_conv = Conversation(id=conv_id or str(uuid.uuid4()))
        _conversations[new_conv.id] = new_conv
        return new_conv
    return _conversations[conv_id]


def get_or_create_session(conv_id: str, model_name: Optional[str] = None) -> core.AgentSession:
    if conv_id not in _agent_sessions:
        _agent_sessions[conv_id] = core.AgentSession(
            session_id=conv_id,
            model_name=model_name or core.DEFAULT_MODEL
        )
    return _agent_sessions[conv_id]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def api_health():
    """Health check for backend, Gemini API, and desktop accessibility session."""
    health_data = core.check_health()
    active_tasks_count = sum(1 for t in _active_tasks.values() if t.status in ("queued", "running"))
    return {
        "status": health_data["status"],
        "backend": "online",
        "hcu_binary": health_data["hcu_binary"],
        "desktop_session": health_data["desktop_session"],
        "gemini": health_data["gemini"],
        "active_tasks": active_tasks_count,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/conversations")
def list_conversations():
    """List all conversations ordered by last update."""
    convs = list(_conversations.values())
    convs.sort(key=lambda c: c.updated_at, reverse=True)
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "message_count": len(c.messages),
        }
        for c in convs
    ]


@app.post("/api/conversations")
def create_conversation():
    """Create a new conversation session."""
    conv = Conversation()
    _conversations[conv.id] = conv
    return conv


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    """Get the full message history for a conversation."""
    if conv_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversations[conv_id]


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    """Delete a conversation and free its agent session."""
    if conv_id in _conversations:
        del _conversations[conv_id]
    if conv_id in _agent_sessions:
        del _agent_sessions[conv_id]
    return {"ok": True, "message": "Conversation deleted"}


@app.get("/api/screenshots/{filename}")
def get_screenshot(filename: str):
    """Serve a screenshot image captured during desktop task execution."""
    safe_name = Path(filename).name
    # Common screenshot locations
    candidates = [
        Path("/tmp/computer-use") / safe_name,
        Path("/tmp") / safe_name,
        REPO_ROOT / safe_name,
    ]
    for cand in candidates:
        if cand.is_file():
            return FileResponse(str(cand), media_type="image/png")
    raise HTTPException(status_code=404, detail="Screenshot not found")


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """Retrieve status of an asynchronous desktop operation."""
    with _tasks_lock:
        task = _active_tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {
            "task_id": task.task_id,
            "conversation_id": task.conversation_id,
            "status": task.status,
            "elapsed_seconds": round(time.time() - task.start_time, 2),
            "cancelled": task.cancel_event.is_set(),
            "has_result": task.result is not None,
            "error": task.error,
        }


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Request cancellation of an active task."""
    with _tasks_lock:
        task = _active_tasks.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.cancel_event.set()
        task.status = "cancelling"
        return {"ok": True, "task_id": task_id, "status": "cancelling"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard synchronous chat endpoint.
    Accepts user prompt, invokes existing Gemini + HCU agent, updates history, and returns response.
    """
    conv = get_or_create_conversation(request.conversation_id)
    session = get_or_create_session(conv.id, request.model)

    # Save user message
    user_msg = Message(role="user", content=request.message)
    conv.messages.append(user_msg)
    if conv.title == "New Chat":
        snippet = request.message.strip()
        conv.title = snippet[:36] + ("..." if len(snippet) > 36 else "")

    task_id = str(uuid.uuid4())
    task = ActiveTask(task_id, conv.id)
    with _tasks_lock:
        _active_tasks[task_id] = task

    task.status = "running"
    try:
        # Run blocking agent in thread pool
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: session.run_task(
                user_goal=request.message,
                cancel_event=task.cancel_event,
            )
        )
        task.status = "completed"
        task.result = result

        # Check for screenshot in tool calls
        screenshot_url = None
        for tc in result.get("tool_calls", []):
            img_path = tc.get("image_path")
            if img_path and Path(img_path).exists():
                screenshot_url = f"/api/screenshots/{Path(img_path).name}"
                tc["image_url"] = screenshot_url

        assistant_msg = Message(
            role="assistant",
            content=result.get("text", ""),
            tool_calls=result.get("tool_calls", []),
            screenshot_url=screenshot_url,
            status="completed" if not result.get("cancelled") else "cancelled",
        )
        conv.messages.append(assistant_msg)
        conv.updated_at = datetime.now().isoformat()

        return {
            "conversation_id": conv.id,
            "message": assistant_msg.dict(),
            "model": result.get("model"),
            "turns": result.get("turns"),
            "cancelled": result.get("cancelled", False),
        }

    except Exception as exc:
        task.status = "failed"
        task.error = str(exc)
        err_msg = Message(
            role="assistant",
            content=f"An error occurred while executing the desktop task: {exc}",
            status="error"
        )
        conv.messages.append(err_msg)
        conv.updated_at = datetime.now().isoformat()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        with _tasks_lock:
            # Keep in memory for status checks, but trim if over 50
            if len(_active_tasks) > 50:
                oldest = sorted(_active_tasks.keys(), key=lambda k: _active_tasks[k].start_time)[:20]
                for k in oldest:
                    del _active_tasks[k]


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Server-Sent Events (SSE) streaming chat endpoint.
    Emits real-time progress: 'status', 'tool_call', 'tool_result', 'final_response', or 'error'.
    Allows the browser UI to display live execution status as tools run!
    """
    conv = get_or_create_conversation(request.conversation_id)
    session = get_or_create_session(conv.id, request.model)

    user_msg = Message(role="user", content=request.message)
    conv.messages.append(user_msg)
    if conv.title == "New Chat":
        snippet = request.message.strip()
        conv.title = snippet[:36] + ("..." if len(snippet) > 36 else "")

    task_id = str(uuid.uuid4())
    task = ActiveTask(task_id, conv.id)
    with _tasks_lock:
        _active_tasks[task_id] = task

    event_queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def sync_on_status(status_str: str):
        asyncio.run_coroutine_threadsafe(
            event_queue.put({"type": "status", "data": {"status": status_str, "task_id": task_id}}),
            loop,
        )

    def sync_on_tool_call(tool: str, summary: str, args: dict):
        asyncio.run_coroutine_threadsafe(
            event_queue.put({
                "type": "tool_call",
                "data": {"tool": tool, "summary": summary, "args": args, "task_id": task_id}
            }),
            loop,
        )

    def sync_on_tool_result(tool: str, output: str, image_path: Optional[str]):
        img_url = f"/api/screenshots/{Path(image_path).name}" if image_path and Path(image_path).exists() else None
        asyncio.run_coroutine_threadsafe(
            event_queue.put({
                "type": "tool_result",
                "data": {
                    "tool": tool,
                    "output": output,
                    "image_url": img_url,
                    "task_id": task_id,
                }
            }),
            loop,
        )

    def run_agent_in_thread():
        try:
            task.status = "running"
            result = session.run_task(
                user_goal=request.message,
                on_status=sync_on_status,
                on_tool_call=sync_on_tool_call,
                on_tool_result=sync_on_tool_result,
                cancel_event=task.cancel_event,
            )
            task.status = "completed"
            task.result = result

            screenshot_url = None
            for tc in result.get("tool_calls", []):
                img_path = tc.get("image_path")
                if img_path and Path(img_path).exists():
                    screenshot_url = f"/api/screenshots/{Path(img_path).name}"
                    tc["image_url"] = screenshot_url

            assistant_msg = Message(
                role="assistant",
                content=result.get("text", ""),
                tool_calls=result.get("tool_calls", []),
                screenshot_url=screenshot_url,
                status="completed" if not result.get("cancelled") else "cancelled",
            )
            conv.messages.append(assistant_msg)
            conv.updated_at = datetime.now().isoformat()

            asyncio.run_coroutine_threadsafe(
                event_queue.put({
                    "type": "final_response",
                    "data": {
                        "conversation_id": conv.id,
                        "task_id": task_id,
                        "message": assistant_msg.dict(),
                        "model": result.get("model"),
                        "turns": result.get("turns"),
                        "cancelled": result.get("cancelled", False),
                    }
                }),
                loop,
            )
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            err_msg = Message(
                role="assistant",
                content=f"An error occurred while executing the desktop task: {exc}",
                status="error"
            )
            conv.messages.append(err_msg)
            conv.updated_at = datetime.now().isoformat()

            asyncio.run_coroutine_threadsafe(
                event_queue.put({
                    "type": "error",
                    "data": {"error": str(exc), "task_id": task_id}
                }),
                loop,
            )
        finally:
            asyncio.run_coroutine_threadsafe(
                event_queue.put({"type": "done", "data": {}}),
                loop,
            )

    # Start thread
    threading.Thread(target=run_agent_in_thread, daemon=True).start()

    async def event_generator():
        # First send task_created event
        yield f"event: task_created\ndata: {json.dumps({'task_id': task_id, 'conversation_id': conv.id})}\n\n"
        while True:
            item = await event_queue.get()
            event_type = item.get("type")
            if event_type == "done":
                break
            payload = json.dumps(item.get("data", {}))
            yield f"event: {event_type}\ndata: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.on_event("shutdown")
def on_shutdown():
    """Cleanup sessions and active tasks on server shutdown."""
    with _tasks_lock:
        for task in _active_tasks.values():
            task.cancel_event.set()
    _agent_sessions.clear()


from fastapi.staticfiles import StaticFiles

# Serve frontend static build if present
DIST_DIR = REPO_ROOT / "frontend" / "dist"
if DIST_DIR.is_dir():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        index_path = DIST_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404, detail="Frontend build index.html not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
