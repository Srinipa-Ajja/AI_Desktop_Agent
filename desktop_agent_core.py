"""
Core Desktop Agent Service
==========================
Reusable agent service integrating Google Gemini with Microsoft Hybrid Computer Use (HCU).
Can be driven by the terminal CLI (chat_agent.py) or the FastAPI web backend.
"""

import os
import sys
import json
import time
import uuid
import threading
import subprocess
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent
HCU_BINARY = REPO_ROOT / "artifacts" / "computer-use"

# Ensure sdk/python is in sys.path
SDK_PATH = REPO_ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

# Ensure .site_packages is in sys.path if present
SITE_PACKAGES = REPO_ROOT / ".site_packages"
if SITE_PACKAGES.is_dir() and str(SITE_PACKAGES) not in sys.path:
    sys.path.insert(0, str(SITE_PACKAGES))

try:
    import hcu_sdk as hcu
except ImportError:
    hcu = None

# Desktop environment keys needed for AT-SPI2 and X11
_DESKTOP_ENV_KEYS = [
    "DISPLAY",
    "XAUTHORITY",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "WAYLAND_DISPLAY",
    "GTK_MODULES",
    "QT_ACCESSIBILITY",
    "GTK_IM_MODULE",
    "QT_IM_MODULE",
    "XMODIFIERS",
    "NO_AT_BRIDGE",
]

# Models in order of availability and quota stability
DEFAULT_MODEL = "gemini-3.1-flash-lite"
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
]

_desktop_client = None
_desktop_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Environment & API Key Resolution
# ---------------------------------------------------------------------------

def get_gemini_api_key() -> str:
    """Resolve Gemini API key from environment, .env file, or system config."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key and not key.startswith("YOUR_"):
        return key

    # Check workspace .env
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and not val.startswith("YOUR_"):
                    os.environ["GEMINI_API_KEY"] = val
                    return val

    # Check ~/.env or /home/user/api_google
    home = Path.home()
    api_google_file = home / "api_google"
    if api_google_file.is_file():
        val = api_google_file.read_text().strip()
        if val and not val.startswith("YOUR_"):
            os.environ["GEMINI_API_KEY"] = val
            return val

    home_env = home / ".env"
    if home_env.is_file():
        for line in home_env.read_text().splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and not val.startswith("YOUR_"):
                    os.environ["GEMINI_API_KEY"] = val
                    return val

    return ""


def get_hcu_env() -> dict:
    """Build the subprocess environment for HCU with desktop session vars."""
    env = {k: v for k, v in os.environ.items()}
    uid = os.getuid()

    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        dbus_path = f"/run/user/{uid}/bus"
        if os.path.exists(dbus_path):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={dbus_path}"

    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"

    if not env.get("XAUTHORITY"):
        candidates = [
            f"/run/user/{uid}/gdm/Xauthority",
            str(Path.home() / ".Xauthority"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                env["XAUTHORITY"] = cand
                break

    for key in _DESKTOP_ENV_KEYS:
        val = os.environ.get(key, "")
        if val:
            env[key] = val

    return env


# ---------------------------------------------------------------------------
# HCU Daemon & Client
# ---------------------------------------------------------------------------

def get_desktop():
    """Get or initialize the persistent HCU daemon connection."""
    global _desktop_client
    if _desktop_client is not None:
        return _desktop_client

    if hcu is None or not HCU_BINARY.is_file():
        return None

    socket_dir = REPO_ROOT / ".hcu"
    socket_dir.mkdir(parents=True, exist_ok=True)
    socket_path = socket_dir / "desktop.sock"

    os.environ["HCU_BIN"] = str(HCU_BINARY)
    os.environ["HCU_SOCKET"] = str(socket_path)

    try:
        subprocess.run(
            [str(HCU_BINARY), "daemon", "start", "--socket", str(socket_path)],
            capture_output=True,
            timeout=10,
            env=get_hcu_env(),
        )
        transport = hcu.SocketTransport(str(socket_path))
        _desktop_client = hcu.Desktop(transport)
    except Exception:
        _desktop_client = None

    return _desktop_client


def check_health() -> Dict[str, Any]:
    """Check status of HCU binary, daemon/accessibility session, and Gemini API."""
    binary_ok = HCU_BINARY.is_file()
    api_key = get_gemini_api_key()
    api_key_configured = bool(api_key)

    # Test desktop accessibility / X11
    desktop_accessible = False
    desktop_message = ""
    try:
        env = get_hcu_env()
        cmd = [str(HCU_BINARY), "call", "AX", "--args", '{"mode":"apps"}']
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
        if res.returncode == 0:
            desktop_accessible = True
            desktop_message = "Active desktop session connected (AT-SPI2 / X11)"
        else:
            desktop_message = res.stderr or res.stdout or "Desktop call returned error"
    except Exception as e:
        desktop_message = str(e)

    return {
        "status": "healthy" if (binary_ok and desktop_accessible and api_key_configured) else "degraded",
        "hcu_binary": {
            "path": str(HCU_BINARY),
            "exists": binary_ok,
        },
        "desktop_session": {
            "accessible": desktop_accessible,
            "display": get_hcu_env().get("DISPLAY", ":0"),
            "message": desktop_message,
        },
        "gemini": {
            "key_configured": api_key_configured,
            "default_model": DEFAULT_MODEL,
            "available_fallbacks": FALLBACK_MODELS,
        },
    }


# ---------------------------------------------------------------------------
# Tool Execution
# ---------------------------------------------------------------------------

def call_ax(args_dict: dict) -> str:
    """Call AX tool via persistent daemon, falling back to direct CLI."""
    d = get_desktop()
    if d is not None:
        try:
            rec = d.call("AX", args_dict)
            return json.dumps(rec, default=str)
        except getattr(hcu, "HcuError", Exception) as exc:
            return json.dumps(getattr(exc, "record", {"ok": False, "message": str(exc)}), default=str)
        except Exception:
            pass

    cmd = [str(HCU_BINARY), "call", "AX", "--args", json.dumps(args_dict)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20, env=get_hcu_env())
        return res.stdout or res.stderr or '{"ok":false,"message":"No output"}'
    except Exception as exc:
        return json.dumps({"ok": False, "message": str(exc)})


def call_gui(args_dict: dict) -> tuple[str, str | None]:
    """Call GUI tool via persistent daemon, returning (output_json, image_path)."""
    image_path = None
    output = None
    d = get_desktop()

    if d is not None:
        try:
            rec = d.call("GUI", args_dict)
            output = json.dumps(rec, default=str)
            if hasattr(rec, "screen") and getattr(rec.screen, "image", None):
                image_path = rec.screen.image
            elif isinstance(rec, dict):
                if rec.get("screen", {}).get("image"):
                    image_path = rec["screen"]["image"]
                elif rec.get("image"):
                    image_path = rec["image"]
        except getattr(hcu, "HcuError", Exception) as exc:
            output = json.dumps(getattr(exc, "record", {"ok": False, "message": str(exc)}), default=str)
        except Exception:
            output = None

    if output is None:
        cmd = [str(HCU_BINARY), "call", "GUI", "--args", json.dumps(args_dict)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25, env=get_hcu_env())
            output = res.stdout or res.stderr or '{"ok":false,"message":"No output"}'
            try:
                data = json.loads(output)
                for item in data.get("content", []):
                    if item.get("type") == "image" and item.get("path"):
                        image_path = item["path"]
                if not image_path:
                    img = data.get("screen", {}).get("image") or data.get("image")
                    if img and Path(img).exists():
                        image_path = img
            except Exception:
                pass
        except Exception as exc:
            output = json.dumps({"ok": False, "message": str(exc)})

    return output or "{}", image_path


def call_shell(command: str) -> str:
    """Execute a shell command (e.g. 'firefox &', 'wmctrl -l')."""
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            env=get_hcu_env(),
        )
        out = (res.stdout or "") + (res.stderr or "")
        return out.strip() or f"Command executed successfully (exit code {res.returncode})"
    except subprocess.TimeoutExpired:
        return "Command started in background."
    except Exception as exc:
        return f"Error executing shell command: {exc}"


# ---------------------------------------------------------------------------
# Gemini Tool Declarations & Instruction
# ---------------------------------------------------------------------------

def build_gemini_tools():
    from google.genai import types

    ax_tool = types.FunctionDeclaration(
        name="hcu_ax",
        description=(
            "Accessibility tool for application windows. "
            "mode='apps': List open application windows (returns wN refs). "
            "mode='observe': Inspect controls of a window (window_ref='w1'). "
            "mode='act': Click/type/keypress on accessibility elements (rN refs)."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "mode": types.Schema(
                    type=types.Type.STRING,
                    description="apps (list windows), observe (inspect UI), or act (click/type)",
                ),
                "window_ref": types.Schema(
                    type=types.Type.STRING,
                    description="Window reference from apps (e.g. 'w1')",
                ),
                "actions": types.Schema(
                    type=types.Type.ARRAY,
                    description="List of action objects for act mode (e.g. [{'type':'click', 'ref':'r12'}])",
                    items=types.Schema(type=types.Type.OBJECT),
                ),
            },
            required=["mode"],
        ),
    )

    gui_tool = types.FunctionDeclaration(
        name="hcu_gui",
        description=(
            "Visual GUI tool for screen capture and mouse/keyboard input. "
            "To take a screenshot: actions=[{'type':'screenshot'}]. "
            "To click: actions=[{'type':'click', 'x': 500, 'y': 300}]. "
            "To type: actions=[{'type':'type', 'text': 'Hello'}]."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "actions": types.Schema(
                    type=types.Type.ARRAY,
                    description="List of GUI action objects.",
                    items=types.Schema(type=types.Type.OBJECT),
                ),
            },
            required=["actions"],
        ),
    )

    shell_tool = types.FunctionDeclaration(
        name="run_shell",
        description="Run a shell command on Linux. Use this to launch apps (e.g. 'firefox &', 'google-chrome &', 'nautilus &') or run terminal commands.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "command": types.Schema(
                    type=types.Type.STRING,
                    description="Shell command string to run",
                ),
            },
            required=["command"],
        ),
    )

    return types.Tool(function_declarations=[ax_tool, gui_tool, shell_tool])


SYSTEM_INSTRUCTION = """\
You are an autonomous Linux desktop assistant.
You can perceive and control the desktop through three tools:
1. run_shell: Launch applications (e.g., 'firefox &', 'google-chrome &', 'libreoffice &') or check terminal info ('wmctrl -l').
2. hcu_ax: Check open windows with mode='apps' or inspect controls with mode='observe'.
3. hcu_gui: Take screenshots (actions=[{'type': 'screenshot'}]) or send mouse/key input.

BEHAVIOR RULES:
- Once an action is performed, report the result immediately to the user and stop. DO NOT loop repeatedly.
- If asked to "open <app>": Run run_shell(command='<app> &') once, then immediately tell the user the app has been launched.
- If asked to "list windows": Run hcu_ax(mode='apps') or run_shell(command='wmctrl -l') once, then present the open windows list to the user.
- If asked to "take a screenshot": Run hcu_gui(actions=[{'type': 'screenshot'}]) once, and describe what is visible on the screen.
- Keep your answers concise and directly answer the user's prompt.
"""


# ---------------------------------------------------------------------------
# Agent Conversation Session
# ---------------------------------------------------------------------------

class AgentSession:
    def __init__(self, session_id: str = None, model_name: str = DEFAULT_MODEL):
        self.session_id = session_id or str(uuid.uuid4())
        self.model_name = model_name
        self.client = None
        self.chat = None
        self.tools = None
        self.messages: List[Dict[str, Any]] = []
        self._init_client()

    def _init_client(self):
        from google import genai
        from google.genai import types

        api_key = get_gemini_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)
        self.tools = build_gemini_tools()

        # Try initial model with fallback
        chat = None
        candidates = [self.model_name] + [m for m in FALLBACK_MODELS if m != self.model_name]
        for candidate in candidates:
            try:
                chat = self.client.chats.create(
                    model=candidate,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        tools=[self.tools],
                        temperature=0.1,
                    ),
                )
                self.model_name = candidate
                break
            except Exception:
                continue

        if not chat:
            raise RuntimeError("Could not initialize chat session with any supported Gemini model.")
        self.chat = chat

    def send_with_retry(self, message, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                return self.chat.send_message(message)
            except Exception as exc:
                err_msg = str(exc)
                if ("503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg) and attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 3)
                else:
                    raise

    def run_task(
        self,
        user_goal: str,
        max_turns: int = 5,
        on_status: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        on_tool_result: Optional[Callable[[str, str, Optional[str]], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> Dict[str, Any]:
        from google.genai import types

        # Acquire desktop lock to prevent concurrent task interference on shared desktop
        with _desktop_lock:
            if on_status:
                on_status("Understanding request")

            tool_records: List[Dict[str, Any]] = []
            screenshot_path = None

            try:
                response = self.send_with_retry(user_goal)
            except Exception as exc:
                err_str = str(exc)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str:
                    # Try fallback model
                    switched = False
                    for fb in FALLBACK_MODELS:
                        if fb != self.model_name:
                            try:
                                self.chat = self.client.chats.create(
                                    model=fb,
                                    config=types.GenerateContentConfig(
                                        system_instruction=SYSTEM_INSTRUCTION,
                                        tools=[self.tools],
                                        temperature=0.1,
                                    ),
                                )
                                self.model_name = fb
                                response = self.send_with_retry(user_goal)
                                switched = True
                                break
                            except Exception:
                                continue
                    if not switched:
                        raise
                else:
                    raise

            turns = 0
            while turns < max_turns:
                if cancel_event and cancel_event.is_set():
                    if on_status:
                        on_status("Task cancelled by user")
                    return {
                        "text": "Task was cancelled by the user.",
                        "tool_calls": tool_records,
                        "cancelled": True,
                        "turns": turns,
                        "model": self.model_name,
                    }

                turns += 1
                function_calls = response.function_calls

                if not function_calls:
                    final_text = response.text or "(Done)"
                    if on_status:
                        on_status("Task completed")
                    return {
                        "text": final_text,
                        "tool_calls": tool_records,
                        "cancelled": False,
                        "turns": turns,
                        "model": self.model_name,
                    }

                if on_status:
                    on_status("Executing desktop task")

                result_parts = []
                for call in function_calls:
                    if cancel_event and cancel_event.is_set():
                        break

                    fname = call.name
                    fargs = dict(call.args)
                    summary = (
                        fargs.get("mode")
                        or fargs.get("command")
                        or (fargs.get("actions", [{}])[0].get("type") if fargs.get("actions") else "?")
                    )

                    if on_tool_call:
                        on_tool_call(fname, str(summary), fargs)

                    if on_status:
                        on_status(f"Executing {fname} ({summary})")

                    tool_output = ""
                    image_path = None

                    if fname == "hcu_ax":
                        tool_output = call_ax(fargs)
                    elif fname == "hcu_gui":
                        tool_output, image_path = call_gui(fargs)
                        if image_path:
                            screenshot_path = image_path
                    elif fname == "run_shell":
                        cmd = fargs.get("command", "")
                        tool_output = call_shell(cmd)
                    else:
                        tool_output = json.dumps({"ok": False, "message": f"Unknown tool: {fname}"})

                    if on_status:
                        on_status("Waiting for tool result")

                    if on_tool_result:
                        on_tool_result(fname, tool_output[:300], image_path)

                    tool_records.append({
                        "tool": fname,
                        "summary": summary,
                        "args": fargs,
                        "output": tool_output,
                        "image_path": image_path,
                    })

                    result_parts.append(
                        types.Part.from_function_response(
                            name=fname,
                            response={"result": tool_output},
                        )
                    )

                    if image_path and Path(image_path).exists():
                        try:
                            with open(image_path, "rb") as f:
                                img_bytes = f.read()
                            result_parts.append(
                                types.Part.from_bytes(data=img_bytes, mime_type="image/png")
                            )
                        except Exception:
                            pass

                if cancel_event and cancel_event.is_set():
                    return {
                        "text": "Task was cancelled before subsequent actions.",
                        "tool_calls": tool_records,
                        "cancelled": True,
                        "turns": turns,
                        "model": self.model_name,
                    }

                if on_status:
                    on_status("Understanding tool results")

                response = self.send_with_retry(result_parts)

            final_text = response.text or "Task finished."
            if on_status:
                on_status("Task completed")
            return {
                "text": final_text,
                "tool_calls": tool_records,
                "cancelled": False,
                "turns": turns,
                "model": self.model_name,
            }
