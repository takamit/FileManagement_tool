from __future__ import annotations
from datetime import datetime

class LogManager:
    def __init__(self) -> None:
        self.logs = {
            "all": [],
            "success": [],
            "error": [],
            "stopped": [],
            "skip": [],
            "info": [],
        }

    def clear(self) -> None:
        for k in self.logs:
            self.logs[k].clear()

    def add(self, kind: str, message: str) -> str:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {message}"
        self.logs["all"].append(line)
        if kind not in self.logs:
            kind = "info"
        if kind != "all":
            self.logs[kind].append(line)
        return line

    def get_text(self, kind: str) -> str:
        return "\n".join(self.logs.get(kind, []))
