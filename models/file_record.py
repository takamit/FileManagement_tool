from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class FileRecord:
    path: Path
    name: str
    extension: str
    size: int
    modified_at: datetime
    sha256: Optional[str] = None
    normalized_name: str = ""
    series_key: Optional[str] = None
    version_score: int = 0
    category: str = "Unclassified"
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: Path) -> "FileRecord":
        stat = path.stat()
        return cls(
            path=path,
            name=path.name,
            extension=path.suffix.lower(),
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime),
        )
