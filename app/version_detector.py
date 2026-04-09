from __future__ import annotations

from collections import defaultdict

from models.file_record import FileRecord
from models.result_models import UpdateCandidate


class VersionDetector:
    def detect(self, files: list[FileRecord]) -> list[UpdateCandidate]:
        grouped: dict[tuple[str, str], list[FileRecord]] = defaultdict(list)
        for file in files:
            grouped[(file.normalized_name, file.extension)].append(file)

        results: list[UpdateCandidate] = []
        for (_, _), group in grouped.items():
            if len(group) < 2:
                continue
            if any(file.series_key for file in group):
                # 単純連番を誤って版管理扱いしない
                continue

            sorted_group = sorted(
                group,
                key=lambda x: (x.version_score, x.modified_at.timestamp(), x.size),
            )
            old_file = sorted_group[0]
            new_file = sorted_group[-1]
            if old_file.path == new_file.path:
                continue
            if new_file.modified_at <= old_file.modified_at and new_file.version_score <= old_file.version_score:
                continue

            confidence = 0.55
            reasons: list[str] = []
            if new_file.version_score > old_file.version_score:
                confidence += 0.2
                reasons.append("版番号が高い")
            if new_file.modified_at > old_file.modified_at:
                confidence += 0.15
                reasons.append("更新日時が新しい")
            if old_file.size and abs(new_file.size - old_file.size) / max(old_file.size, 1) < 0.4:
                confidence += 0.1
                reasons.append("サイズ差が極端ではない")

            if reasons:
                results.append(
                    UpdateCandidate(
                        old_file=old_file,
                        new_file=new_file,
                        reason=" / ".join(reasons),
                        confidence=min(confidence, 0.95),
                    )
                )
        return results
