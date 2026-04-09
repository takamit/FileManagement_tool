from __future__ import annotations

from pathlib import Path

from models.file_record import FileRecord


class FileClassifier:
    def __init__(self, rules: dict[str, list[str]]) -> None:
        self.rules = rules

    def classify(self, files: list[FileRecord]) -> None:
        for file in files:
            file.category = self._classify_one(file)

    def _classify_one(self, file: FileRecord) -> str:
        lower_name = file.name.lower()
        for category, keywords in self.rules.items():
            for keyword in keywords:
                if keyword.startswith('.') and keyword == file.extension:
                    return category
                if keyword.lower() in lower_name:
                    return category
        return "Unclassified"
