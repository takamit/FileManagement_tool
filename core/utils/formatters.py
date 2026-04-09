from __future__ import annotations

def bytes_text(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    n = float(max(0, value))
    for unit in units:
        if n < 1024 or unit == units[-1]:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{value} B"
