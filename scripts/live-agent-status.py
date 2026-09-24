"""Small always-visible status and stop control for the local DSP experiment worker."""

import json
import os
import tkinter as tk
from pathlib import Path


DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "DSPAgent" / "codex-experiments-20260924"
STATUS = DATA_DIR / "live-agent-status.json"
STOP = DATA_DIR / "live-agent.stop"


def main():
    root = tk.Tk()
    root.title("DSP AI Agent - STATUS")
    root.geometry("700x210+1200+20")
    root.attributes("-topmost", True)
    root.configure(bg="#17212b")

    headline = tk.StringVar(value="Waiting for the agent...")
    detail = tk.StringVar(value=str(STATUS))
    last_action = ""
    tk.Label(root, textvariable=headline, font=("Segoe UI", 17, "bold"), fg="#72e1b4",
             bg="#17212b", anchor="w").pack(fill="x", padx=16, pady=(15, 4))
    tk.Label(root, textvariable=detail, font=("Segoe UI", 10), fg="white",
             bg="#17212b", anchor="nw", justify="left", wraplength=660).pack(
                 fill="both", expand=True, padx=16)

    def stop():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        STOP.write_text("Stop after the current attempt.\n", encoding="utf-8")
        headline.set("Stop requested")

    tk.Button(root, text="Stop after attempt", command=stop, font=("Segoe UI", 11),
              bg="#f08c82", fg="black").pack(anchor="e", padx=16, pady=(2, 12))

    def refresh():
        nonlocal last_action
        try:
            status = json.loads(STATUS.read_text(encoding="utf-8-sig"))
            root.title(f"DSP AI Agent - {status['state'].upper()}")
            headline.set(f"DSP AI Agent: {status['state']}  "
                         f"{status['completed_attempts']}/{status['max_attempts']}")
            message = status.get("message", "")
            last_action = status.get("last_action", last_action)
            if status["state"] == "completed":
                last_action = message
            detail.set(message + ("\nLast action: " + last_action
                                  if last_action and status["state"] in ("planning", "stopped") else ""))
        except (OSError, ValueError, KeyError):
            detail.set("Waiting for live status from the local worker.")
        root.after(1000, refresh)

    refresh()
    root.mainloop()


if __name__ == "__main__":
    main()
