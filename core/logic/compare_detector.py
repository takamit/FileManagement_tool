from __future__ import annotations

from collections import defaultdict

from core.utils.hasher import compute_sha256
from core.utils.progress_service import ProgressService
from core.models.file_record import FileRecord
from core.models.result_models import DuplicateGroup, UpdateCandidate


class CompareDetector:
    def __init__(self, progress: ProgressService) -> None:
        self.progress = progress

    def detect(
        self,
        source_files: list[FileRecord],
        reference_files: list[FileRecord],
    ) -> tuple[list[DuplicateGroup], list[UpdateCandidate], list[str]]:
        errors: list[str] = []
        all_targets = source_files + reference_files
        total_hash = len(all_targets)
        for index, file in enumerate(all_targets, start=1):
            if file.sha256:
                continue
            self.progress.update('比較ハッシュ判定', index, total_hash, file.name)
            try:
                file.sha256 = compute_sha256(file.path)
            except Exception as exc:
                errors.append(f'比較ハッシュ計算失敗: {file.path} | {exc}')

        ref_hash_map: dict[str, list[FileRecord]] = defaultdict(list)
        for file in reference_files:
            if file.sha256:
                ref_hash_map[file.sha256].append(file)

        duplicate_groups: list[DuplicateGroup] = []
        for file in source_files:
            if file.sha256 and file.sha256 in ref_hash_map:
                duplicate_groups.append(DuplicateGroup(sha256=file.sha256, files=[file, *ref_hash_map[file.sha256]]))

        ref_name_map: dict[tuple[str, str], list[FileRecord]] = defaultdict(list)
        for file in reference_files:
            ref_name_map[(file.normalized_name, file.extension)].append(file)

        update_candidates: list[UpdateCandidate] = []
        total = len(source_files)
        for index, source in enumerate(source_files, start=1):
            self.progress.update('比較更新候補判定', index, total, source.name)
            key = (source.normalized_name, source.extension)
            refs = ref_name_map.get(key, [])
            if not refs:
                continue
            if source.series_key:
                continue
            newest_ref = max(refs, key=lambda x: (x.version_score, x.modified_at.timestamp(), x.size))
            if newest_ref.path == source.path:
                continue
            if newest_ref.modified_at <= source.modified_at and newest_ref.version_score <= source.version_score:
                continue

            reason_parts: list[str] = []
            confidence = 0.6
            if newest_ref.version_score > source.version_score:
                reason_parts.append('比較先の版番号が高い')
                confidence += 0.15
            if newest_ref.modified_at > source.modified_at:
                reason_parts.append('比較先の更新日時が新しい')
                confidence += 0.15
            if source.size and abs(newest_ref.size - source.size) / max(source.size, 1) < 0.5:
                reason_parts.append('サイズ差が極端ではない')
                confidence += 0.05

            update_candidates.append(
                UpdateCandidate(
                    old_file=source,
                    new_file=newest_ref,
                    reason=' / '.join(reason_parts) or '比較先により新しい候補あり',
                    confidence=min(confidence, 0.95),
                    scope='compare',
                )
            )
        return duplicate_groups, update_candidates, errors
