from __future__ import annotations

from collections import defaultdict

from core.utils.hasher import compute_sha256
from core.utils.progress_service import ProgressService
from core.models.file_record import FileRecord
from core.models.result_models import DuplicateGroup


class DuplicateDetector:
    def __init__(self, progress: ProgressService) -> None:
        self.progress = progress

    def detect(self, files: list[FileRecord]) -> tuple[list[DuplicateGroup], list[str]]:
        errors: list[str] = []
        size_groups: dict[int, list[FileRecord]] = defaultdict(list)
        for file in files:
            size_groups[file.size].append(file)

        hash_groups: dict[str, list[FileRecord]] = defaultdict(list)
        candidates = [group for group in size_groups.values() if len(group) > 1]
        flat = [item for group in candidates for item in group]
        total = len(flat)

        for index, file in enumerate(flat, start=1):
            self.progress.update("重複判定", index, total, file.name)
            try:
                file.sha256 = compute_sha256(file.path)
                hash_groups[file.sha256].append(file)
            except Exception as exc:
                errors.append(f"ハッシュ計算失敗: {file.path} | {exc}")

        groups = [DuplicateGroup(sha256=k, files=v) for k, v in hash_groups.items() if len(v) > 1]
        return groups, errors
