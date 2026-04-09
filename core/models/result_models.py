from __future__ import annotations

from dataclasses import dataclass, field

from core.models.file_record import FileRecord


@dataclass(slots=True)
class DuplicateGroup:
    sha256: str
    files: list[FileRecord] = field(default_factory=list)


@dataclass(slots=True)
class UpdateCandidate:
    old_file: FileRecord
    new_file: FileRecord
    reason: str
    confidence: float
    scope: str = "internal"


@dataclass(slots=True)
class SeriesGroup:
    key: str
    files: list[FileRecord] = field(default_factory=list)


@dataclass(slots=True)
class ScanResults:
    files: list[FileRecord] = field(default_factory=list)
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    update_candidates: list[UpdateCandidate] = field(default_factory=list)
    series_groups: list[SeriesGroup] = field(default_factory=list)
    compare_duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    compare_update_candidates: list[UpdateCandidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
