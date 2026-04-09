from __future__ import annotations

from collections import defaultdict

from models.file_record import FileRecord
from models.result_models import SeriesGroup


class SeriesDetector:
    def detect(self, files: list[FileRecord]) -> list[SeriesGroup]:
        groups: dict[str, list[FileRecord]] = defaultdict(list)
        for file in files:
            if file.series_key:
                groups[f"{file.series_key}|{file.extension}"].append(file)
        return [SeriesGroup(key=key, files=items) for key, items in groups.items() if len(items) > 1]
