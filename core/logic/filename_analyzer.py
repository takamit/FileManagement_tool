from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

VERSION_PATTERNS = [
    re.compile(r"(?i)(?:^|[_\-\s])(v|ver|rev)\s*([0-9]+)$"),
    re.compile(r"(?i)(?:^|[_\-\s])(final|fix|updated|update)$"),
    re.compile(r"(?i)(修正|修正版|改訂|更新|最終|最終版)$"),
]
SERIES_PATTERN = re.compile(r"^(.*?)(\d{1,4})$")
COPY_PATTERN = re.compile(r"(?i)(?:^|[_\-\s])(copy|コピー)$")
DATE_PATTERN = re.compile(r"(?:19|20)\d{2}[-_]?\d{2}[-_]?\d{2}")


@dataclass(slots=True)
class NameAnalysis:
    stem: str
    normalized_name: str
    series_key: str | None
    version_score: int
    is_series_like: bool
    is_version_like: bool


class FilenameAnalyzer:
    def analyze(self, path: Path) -> NameAnalysis:
        stem = path.stem
        working = DATE_PATTERN.sub("", stem).strip(" _-")
        version_score = 0
        is_version_like = False

        for pattern in VERSION_PATTERNS:
            match = pattern.search(working)
            if match:
                is_version_like = True
                token = match.group(0)
                if any(ch.isdigit() for ch in token):
                    digits = re.findall(r"\d+", token)
                    version_score = int(digits[-1]) if digits else 1
                else:
                    version_score = max(version_score, 999)
                working = working[: match.start()].strip(" _-")
                break

        working = COPY_PATTERN.sub("", working).strip(" _-")

        series_key = None
        is_series_like = False
        series_match = SERIES_PATTERN.match(working)
        if series_match and not is_version_like:
            prefix, number = series_match.groups()
            if prefix.strip():
                series_key = prefix.strip(" _-")
                is_series_like = True

        normalized_name = re.sub(r"[\s_\-]+", " ", working).strip().lower()
        return NameAnalysis(
            stem=stem,
            normalized_name=normalized_name or stem.lower(),
            series_key=series_key.lower() if series_key else None,
            version_score=version_score,
            is_series_like=is_series_like,
            is_version_like=is_version_like,
        )
