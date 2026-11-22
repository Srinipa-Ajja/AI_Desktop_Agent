#!/usr/bin/env python3
"""
Gemini + Hybrid Computer Use (HCU) Terminal Chat Agent
=======================================================
Interactive terminal agent that uses Google Gemini + the HCU AX/GUI tools
to perceive and operate the Linux desktop.

Usage:
    python3 chat_agent.py                          # prompts for API key
    GEMINI_API_KEY=AIza... python3 chat_agent.py   # from env var
    python3 chat_agent.py --model gemini-3-flash-preview

Requirements:
    pip install google-genai pillow
    artifacts/computer-use  (already built in this repo)
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
HCU_BINARY = REPO_ROOT / "artifacts" / "computer-use"
DEFAULT_MODEL = "gemini-3-flash-preview"
FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]

# Set up paths for hcu_sdk
sys.path.insert(0, str(REPO_ROOT / "sdk" / "python"))
try:
    import hcu_sdk as hcu
except ImportError:
    hcu = None

# Desktop environment forwarding – needed for the AT-SPI2 provider
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

# Global persistent Desktop client instance
_desktop_client = None

# ---------------------------------------------------------------------------
# Startup & Daemon Setup
# ---------------------------------------------------------------------------

def _hcu_env() -> dict:
    """Build the subprocess environment for HCU with desktop session vars."""
    env = {k: v for k, v in os.environ.items()}
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        uid = os.getuid()
        dbus_path = f"/run/user/{uid}/bus"
        if os.path.exists(dbus_path):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={dbus_path}"
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"

    for key in _DESKTOP_ENV_KEYS:
        val = os.environ.get(key, "")
        if val:
            env[key] = val
    return env


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

    # Ensure daemon is running
    try:
        subprocess.run(
            [str(HCU_BINARY), "daemon", "start", "--socket", str(socket_path)],
            capture_output=True,
            timeout=10,
            env=_hcu_env(),
        )
        transport = hcu.SocketTransport(str(socket_path))
        _desktop_client = hcu.Desktop(transport)
    except Exception:
        _desktop_client = None

    return _desktop_client


def check_prerequisites() -> str:
    """Validate binary, install SDK, resolve API key. Returns the key."""
    if not HCU_BINARY.is_file():
        _die(
            f"HCU binary not found at {HCU_BINARY}\n"
            "Build it first:\n"
            "  cd Hybrid-Computer-Use && make build-local"
        )

    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("[*] Installing google-genai…")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "google-genai", "pillow"]
        )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("=" * 60)
        print("  GEMINI_API_KEY is not set.")
        print("=" * 60)
        api_key = input("  Paste your Google Gemini API key: ").strip()
        if not api_key:
            _die("API key required.")
        os.environ["GEMINI_API_KEY"] = api_key

    return api_key


def _die(msg: str) -> None:
    print(f"\n[✗] {msg}", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# HCU tool wrappers (Daemon-backed to preserve refs and frames)
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

    # Direct fallback
    cmd = [str(HCU_BINARY), "call", "AX", "--args", json.dumps(args_dict)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20, env=_hcu_env())
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
            elif rec.get("screen", {}).get("image"):
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
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25, env=_hcu_env())
            output = res.stdout or res.stderr or '{"ok":false,"message":"No output"}'
            data = json.loads(output)
            for item in data.get("content", []):
                if item.get("type") == "image" and item.get("path"):
                    image_path = item["path"]
            if not image_path:
                img = data.get("screen", {}).get("image") or data.get("image")
                if img and Path(img).exists():
                    image_path = img
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
            env=_hcu_env()
        )
        out = (res.stdout or "") + (res.stderr or "")
        return out.strip() or f"Command executed successfully (exit code {res.returncode})"
    except subprocess.TimeoutExpired:
        return "Command started in background."
    except Exception as exc:
        return f"Error executing shell command: {exc}"

# ---------------------------------------------------------------------------
# Gemini tool declarations
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

# ---------------------------------------------------------------------------
# System instruction
# ---------------------------------------------------------------------------

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
# Turn execution with retry & quota guard
# ---------------------------------------------------------------------------

def send_with_retry(chat, message, max_retries: int = 3):
    """Send message with retry on temporary 503 errors."""
    for attempt in range(max_retries):
        try:
            return chat.send_message(message)
        except Exception as exc:
            err_msg = str(exc)
            if ("503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"\n  [Model busy (503)] Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise


def run_task(chat, user_goal: str, verbose: bool = False, max_turns: int = 5) -> None:
    """Execute a user goal with a strictly capped turn limit to conserve quota."""
    from google.genai import types

    print(f"\n{'─'*60}")
    print(f"[You] {user_goal}")
    print(f"{'─'*60}")

    response = send_with_retry(chat, user_goal)
    turns = 0

    while turns < max_turns:
        turns += 1
        function_calls = response.function_calls

        if not function_calls:
            text = response.text or "(Done)"
            print(f"\n[Agent] {text}\n")
            break

        result_parts = []
        for call in function_calls:
            fname = call.name
            fargs = dict(call.args)

            summary = fargs.get("mode") or fargs.get("command") or fargs.get("actions", [{}])[0].get("type", "?")
            print(f"\n  ↳ {fname}({summary!r})")

            tool_output = ""
            image_path = None

            if fname == "hcu_ax":
                tool_output = call_ax(fargs)
                display = tool_output[:160] + "…" if len(tool_output) > 160 else tool_output
                print(f"     → {display}")

            elif fname == "hcu_gui":
                tool_output, image_path = call_gui(fargs)
                display = tool_output[:160] + "…" if len(tool_output) > 160 else tool_output
                print(f"     → {display}")
                if image_path:
                    print(f"     [screenshot saved] {image_path}")

            elif fname == "run_shell":
                cmd = fargs.get("command", "")
                tool_output = call_shell(cmd)
                display = tool_output[:160] + "…" if len(tool_output) > 160 else tool_output
                print(f"     → {display}")

            else:
                tool_output = json.dumps({"ok": False, "message": f"Unknown tool: {fname}"})

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
                    print("     [image attached to model vision]")
                except Exception as exc:
                    print(f"     [image read error: {exc}]")

        response = send_with_retry(chat, result_parts)
    else:
        print("\n[Agent] Task finished.")


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def create_chat_session(client, model_name: str, tool):
    from google.genai import types
    return client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[tool],
            temperature=0.1,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gemini + HCU terminal chat agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--verbose", action="store_true", help="Print verbose output")
    parser.add_argument("--max-turns", type=int, default=5, help="Turn budget per command (default: 5)")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   🚀 Gemini + Hybrid Computer Use  —  Terminal Agent     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    api_key = check_prerequisites()

    from google import genai
    client = genai.Client(api_key=api_key)
    tool = build_gemini_tools()

    # Pre-start daemon
    get_desktop()

    selected_model = args.model
    chat = None
    for candidate in [selected_model] + [m for m in FALLBACK_MODELS if m != selected_model]:
        try:
            chat = create_chat_session(client, candidate, tool)
            selected_model = candidate
            break
        except Exception:
            continue

    if not chat:
        _die("Could not start chat session with any model.")

    print(f"Model  : {selected_model}")
    print(f"Binary : {HCU_BINARY}")
    print()
    print("Type a desktop task or question. Type 'exit' to quit.")
    print("─" * 60)
    print()
    print("💡 Tips:")
    print("  • 'list the windows open'  → shows all desktop windows")
    print("  • 'take a screenshot'      → captures and describes screen")
    print("  • 'open firefox'           → launches Firefox")
    print("  • 'open chrome'            → launches Google Chrome")
    print("  • 'help'                   → show command help")
    print()

    while True:
        try:
            user_input = input("\n[You] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q", ":q"):
            print("Goodbye! 👋")
            break
        if user_input.lower() in ("help", "?"):
            print(
                "\nCommands:\n"
                "  exit / quit — quit the agent\n"
                "  help        — show this help\n"
                "\nExamples:\n"
                "  'list the windows open'\n"
                "  'take a screenshot'\n"
                "  'open firefox'\n"
                "  'open chrome'\n"
            )
            continue

        try:
            run_task(chat, user_input, verbose=args.verbose, max_turns=args.max_turns)
        except KeyboardInterrupt:
            print("\n[Interrupted] Task cancelled.\n")
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                print(f"\n[!] Model {selected_model} reached quota limit.")
                # Try fallback
                switched = False
                for fb in FALLBACK_MODELS:
                    if fb != selected_model:
                        try:
                            print(f"[*] Switching to fallback model {fb}...")
                            new_chat = create_chat_session(client, fb, tool)
                            chat = new_chat
                            selected_model = fb
                            print(f"[✓] Switched to {selected_model}! Retrying your request...")
                            run_task(chat, user_input, verbose=args.verbose, max_turns=args.max_turns)
                            switched = True
                            break
                        except Exception:
                            continue
                if not switched:
                    print("\n[Error] Free-tier quota exceeded on all models for today.")
                    print("Please try again later or add billing in Google AI Studio (https://aistudio.google.com/).")
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                print(f"\n[!] Model {selected_model} is temporarily busy. Please try your request again in a few seconds.")
            else:
                print(f"\n[Error] {exc}\n")


if __name__ == "__main__":
    main()
