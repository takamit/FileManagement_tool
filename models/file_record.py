from dataclasses import dataclass


@dataclass
class FileRecord:
    path: str
    size: int
    suffix: str
