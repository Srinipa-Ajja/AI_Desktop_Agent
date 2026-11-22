#!/usr/bin/env python3
"""
Gemini + Hybrid Computer Use (HCU) Standalone Desktop Agent
Pairs Google's Gemini models with Microsoft's HCU (Hybrid Computer Use) tool engine.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

HCU_BINARY = Path("/home/user/Hybrid-Computer-Use/artifacts/computer-use")

# 1. Check Prerequisites
if not HCU_BINARY.is_file():
    print(f"[-] Error: HCU binary not found at {HCU_BINARY}")
    print("    Please ensure ~/Hybrid-Computer-Use/artifacts/computer-use is built.")
    sys.exit(1)

# Check API Key
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("=" * 60)
    print("GEMINI_API_KEY environment variable is not set.")
    api_key = input("Enter your Google Gemini API Key: ").strip()
    if not api_key:
        print("[-] API key required to proceed.")
        sys.exit(1)
    os.environ["GEMINI_API_KEY"] = api_key

# Ensure google-genai is installed
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("[*] Installing google-genai library...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "google-genai", "pillow"])
    from google import genai
    from google.genai import types

client = genai.Client(api_key=api_key)

# 2. Tool Wrappers for HCU
def run_hcu_ax(mode: str, window_ref: str = "", observe: str = "tree") -> str:
    """
    Query or interact with the Linux Accessibility (AX) tree.
    mode: 'apps' to list all top-level windows (w1, w2, etc.).
          'observe' to get the tree of a window specified by window_ref.
    """
    args = {"mode": mode}
    if window_ref:
        args["window_ref"] = window_ref
    if mode == "observe":
        args["observe"] = observe

    cmd = [str(HCU_BINARY), "call", "AX", "--args", json.dumps(args)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return res.stdout or res.stderr or "No output"
    except Exception as e:
        return f"Error executing AX command: {e}"

def run_hcu_gui(action_type: str, x: int = 0, y: int = 0, text: str = "", keys: str = "") -> str:
    """
    Visual and Input (GUI) actions.
    action_type:
      'screenshot': Captures full screen. Returns image file path.
      'click': Clicks mouse at (x, y) coordinates.
      'type': Types the given text.
      'keypress': Sends keys (e.g., 'Return', 'BackSpace').
    """
    action = {"type": action_type}
    if action_type == "click":
        action["x"] = x
        action["y"] = y
    elif action_type == "type":
        action["text"] = text
    elif action_type == "keypress":
        action["keys"] = [k.strip() for k in keys.split(",") if k.strip()]

    cmd = [str(HCU_BINARY), "call", "GUI", "--args", json.dumps({"actions": [action]})]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return res.stdout or res.stderr or "No output"
    except Exception as e:
        return f"Error executing GUI command: {e}"


# Tool definitions for Gemini
tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="run_hcu_ax",
                description="Query application windows or inspect UI elements using the semantic Accessibility (AX) tree.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "mode": types.Schema(
                            type=types.Type.STRING,
                            description="Mode: 'apps' to list all open windows, or 'observe' to read a window tree."
                        ),
                        "window_ref": types.Schema(
                            type=types.Type.STRING,
                            description="Window reference (e.g. 'w1', 'w2') obtained from apps mode."
                        ),
                        "observe": types.Schema(
                            type=types.Type.STRING,
                            description="Observe detail: 'tree', 'summary', or 'diff'."
                        ),
                    },
                    required=["mode"],
                ),
            ),
            types.FunctionDeclaration(
                name="run_hcu_gui",
                description="Perform visual desktop actions (screenshot) or mouse/keyboard input.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action_type": types.Schema(
                            type=types.Type.STRING,
                            description="Action type: 'screenshot', 'click', 'type', or 'keypress'."
                        ),
                        "x": types.Schema(type=types.Type.INTEGER, description="X pixel coordinate for click"),
                        "y": types.Schema(type=types.Type.INTEGER, description="Y pixel coordinate for click"),
                        "text": types.Schema(type=types.Type.STRING, description="Text to type"),
                        "keys": types.Schema(type=types.Type.STRING, description="Comma-separated keys to press (e.g. 'Return')"),
                    },
                    required=["action_type"],
                ),
            ),
        ]
    )
]

SYSTEM_INSTRUCTION = """You are an autonomous desktop assistant running on Linux.
You can perceive and operate the computer using Hybrid Computer Use (HCU) tools:
1. run_hcu_ax: Use mode='apps' to see what windows are open. Use mode='observe' with window_ref to find buttons, text fields, and UI controls.
2. run_hcu_gui: Use action_type='screenshot' to see the screen visually. Use 'click' at x,y coordinates, 'type' to type text, and 'keypress' for keyboard shortcuts.
Always check current open windows or take a screenshot before clicking.
Report your progress to the user concisely after performing actions.
"""

def execute_agent_turn(user_goal: str):
    print(f"\n[Agent] Starting task: {user_goal}")
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=tools,
            temperature=0.2,
        )
    )

    response = chat.send_message(user_goal)
    max_turns = 10
    turns = 0

    while turns < max_turns:
        turns += 1
        
        # Check if model requested function calls
        function_calls = response.function_calls
        if not function_calls:
            print(f"\n[Assistant]: {response.text}")
            break

        for call in function_calls:
            fname = call.name
            fargs = dict(call.args)
            print(f"  -> Calling tool: {fname}({fargs})")

            tool_result = ""
            image_path = None

            if fname == "run_hcu_ax":
                tool_result = run_hcu_ax(**fargs)
            elif fname == "run_hcu_gui":
                tool_result = run_hcu_gui(**fargs)
                # Check if a screenshot was generated
                try:
                    data = json.loads(tool_result)
                    for item in data.get("content", []):
                        if item.get("type") == "image":
                            image_path = item.get("path")
                except Exception:
                    pass

            print(f"     Result: {tool_result[:160]}...")

            # Build response back to Gemini
            parts = [
                types.Part.from_function_response(
                    name=fname,
                    response={"result": tool_result}
                )
            ]

            # If a screenshot was captured, attach it as vision evidence
            if image_path and os.path.exists(image_path):
                print(f"     [Vision] Attaching screenshot {image_path}")
                with open(image_path, "rb") as img_file:
                    img_bytes = img_file.read()
                    parts.append(
                        types.Part.from_bytes(
                            data=img_bytes,
                            mime_type="image/png"
                        )
                    )

            response = chat.send_message(parts)

def main():
    print("=" * 60)
    print("   🚀 Gemini + Hybrid Computer Use (HCU) Local Agent")
    print("=" * 60)
    print("Model: gemini-2.5-flash")
    print(f"HCU Backend: {HCU_BINARY}")
    print("Ready to automate desktop tasks.\n")

    while True:
        try:
            prompt = input("Enter command (or 'exit' to quit): ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print("Exiting.")
                break
            execute_agent_turn(prompt)
        except KeyboardInterrupt:
            print("\nAborted.")
            break
        except Exception as e:
            print(f"Error during execution: {e}")

if __name__ == "__main__":
    main()
