from __future__ import annotations

import hashlib
import os
import re
import zipfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable

from .content_tools import read_text_preview

VERSION_WORDS = ("v", "ver", "rev", "final", "fix", "更新", "修正", "改訂", "最新版", "最終", "最終版")
TEXT_COMPARE_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".log", ".ini", ".yaml", ".yml", ".docx", ".pdf"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".heic", ".avif"}


@dataclass
class ScanItem:
    category: str
    reason: str
    compare_path: str
    target_path: str
    scope: str
    target_selected: bool = False
    compare_selected: bool = False
    preferred_action: str = "何もしない"
    similarity: float = 0.0
    notes: str = ""
    target_size: int = 0
    compare_size: int = 0
    target_mtime: float = 0.0
    compare_mtime: float = 0.0
    diff_summary: str = ""
    confidence: str = "低"

    def selection_state_text(self) -> str:
        if self.target_selected and self.compare_selected:
            return "両方選択"
        if self.target_selected:
            return "対象フォルダ側"
        if self.compare_selected:
            return "比較フォルダ側"
        return "未選択"


def normalize_base_name(stem: str) -> str:
    s = stem.strip()
    s = re.sub(r"\((\d+)\)$", "", s)
    s = re.sub(r"[_\-\s]+", " ", s)
    s = re.sub(r"(最終版|最終|最新版|修正版|修正|改訂版|改訂)$", "", s)
    s = re.sub(r"\b(v|ver|rev)\s*\d+\b", "", s, flags=re.I)
    return s.strip().lower()


def has_version_word(stem: str) -> bool:
    lower = stem.lower()
    return any(word in lower for word in VERSION_WORDS)


def looks_like_series_only(stem: str) -> bool:
    return bool(re.search(r"[A-Za-zぁ-んァ-ヶ一-龠ー]\d{1,3}$", stem))


def should_skip_path(path: Path, exclude_dirs: list[str], exclude_exts: list[str]) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if any(d.lower() in lower_parts for d in exclude_dirs):
        return True
    if path.suffix.lower() in {e.lower() for e in exclude_exts}:
        return True
    if path.name.startswith("~$") or path.name.endswith(".crdownload"):
        return True
    return False



def count_images_in_zip(zip_path: Path) -> int:
    # zip内zipは再帰しない。中身一覧のみ確認する。
    count = 0
    try:
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            for name in zf.namelist():
                try:
                    lower = name.lower()
                    if lower.endswith("/"):
                        continue
                    ext = Path(lower).suffix.lower()
                    if ext in IMAGE_EXTS:
                        count += 1
                except Exception:
                    continue
    except Exception:
        return 0
    return count


def summarize_special_counts(file_infos: list[dict]) -> dict:
    image_files = 0
    zip_files = 0
    zip_image_files = 0
    for info in file_infos:
        suffix = info.get("suffix", "").lower()
        if suffix in IMAGE_EXTS:
            image_files += 1
        if suffix == ".zip":
            zip_files += 1
            zip_image_files += int(info.get("zip_image_count", 0) or 0)
    return {
        "image_files": image_files,
        "zip_files": zip_files,
        "zip_image_files": zip_image_files,
    }

def iter_files(base_dir: str, exclude_dirs: list[str], exclude_exts: list[str]) -> list[Path]:
    result: list[Path] = []
    exclude_dir_set = {x.lower() for x in exclude_dirs}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d.lower() not in exclude_dir_set]
        for name in files:
            p = Path(root) / name
            if should_skip_path(p, exclude_dirs, exclude_exts):
                continue
            result.append(p)
    return result


def sha256_of_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def quick_text(path: Path, max_chars: int = 8000) -> str:
    return read_text_preview(str(path), max_chars=max_chars)


def build_file_info(paths: Iterable[Path], progress_cb: Callable[[int, int, str], None] | None = None, base_done: int = 0, total_work: int = 1) -> list[dict]:
    paths = list(paths)
    result: list[dict] = []
    total = len(paths)
    for idx, path in enumerate(paths, start=1):
        try:
            stat = path.stat()
            result.append({
                "path": str(path),
                "name": path.name,
                "stem": path.stem,
                "suffix": path.suffix.lower(),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "normalized": normalize_base_name(path.stem),
                "has_version_word": has_version_word(path.stem),
                "looks_like_series_only": looks_like_series_only(path.stem),
                "_hash": None,
                "_preview": None,
                "zip_image_count": count_images_in_zip(path) if path.suffix.lower() == ".zip" else 0,
            })
        except Exception as e:
            result.append({
                "path": str(path),
                "name": path.name,
                "stem": path.stem,
                "suffix": path.suffix.lower(),
                "size": -1,
                "mtime": 0,
                "normalized": normalize_base_name(path.stem),
                "has_version_word": False,
                "looks_like_series_only": False,
                "_hash": None,
                "_preview": None,
                "error": str(e),
                "zip_image_count": 0,
            })
        if progress_cb and (idx == 1 or idx == total or idx % 50 == 0):
            progress_cb(base_done + idx, total_work, f"読込中: {path.name}")
    return result


def get_hash(info: dict) -> str:
    cached = info.get("_hash")
    if cached is None:
        try:
            cached = sha256_of_file(Path(info["path"]))
        except Exception:
            cached = ""
        info["_hash"] = cached
    return cached


def get_preview(info: dict) -> str:
    cached = info.get("_preview")
    if cached is None:
        try:
            cached = quick_text(Path(info["path"]))
        except Exception as e:
            cached = f"(本文取得失敗: {e})"
        info["_preview"] = cached
    return cached


def text_similarity_info(info_a: dict, info_b: dict) -> tuple[float, str]:
    text_a = get_preview(info_a)
    text_b = get_preview(info_b)
    if text_a.startswith("(") and text_b.startswith("("):
        return 0.0, "本文比較は行えませんでした"
    ratio = SequenceMatcher(None, text_a[:5000], text_b[:5000]).ratio()
    return ratio, f"本文の近さ: {ratio * 100:.1f}%"


def shorten_reason(base: str, similarity: float = 0.0) -> str:
    return f"{base} / 近さ {similarity * 100:.1f}%" if similarity > 0 else base


def _make_item(category, reason, compare_path, target_path, scope, target_size, compare_size, target_mtime, compare_mtime, diff_summary, confidence, similarity=0.0, notes="") -> ScanItem:
    return ScanItem(
        category=category,
        reason=reason,
        compare_path=compare_path,
        target_path=target_path,
        scope=scope,
        target_selected=False,
        compare_selected=False,
        preferred_action="何もしない",
        similarity=similarity,
        notes=notes,
        target_size=target_size,
        compare_size=compare_size,
        target_mtime=target_mtime,
        compare_mtime=compare_mtime,
        diff_summary=diff_summary,
        confidence=confidence,
    )


def detect_inside_duplicates(file_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    by_size: dict[int, list[dict]] = {}
    total = max(len(file_infos), 1)
    for idx, info in enumerate(file_infos, start=1):
        if info["size"] >= 0:
            by_size.setdefault(info["size"], []).append(info)
        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "対象フォルダ内の重複を確認中")
    items: list[ScanItem] = []
    for group in by_size.values():
        if len(group) < 2:
            continue
        by_hash: dict[str, list[dict]] = {}
        for info in group:
            h = get_hash(info)
            if h:
                by_hash.setdefault(h, []).append(info)
        for hashed_group in by_hash.values():
            if len(hashed_group) < 2:
                continue
            group_sorted = sorted(hashed_group, key=lambda x: (x["mtime"], x["path"]))
            compare_info = group_sorted[-1]
            for target in group_sorted[:-1]:
                items.append(_make_item(
                    "同一ファイル", "対象フォルダ内で中身が完全一致しています", compare_info["path"], target["path"], "対象フォルダ内",
                    target["size"], compare_info["size"], target["mtime"], compare_info["mtime"], "内容は完全一致です", "高", 1.0,
                    "対象側・比較側を個別に選択できます。"
                ))
    return items


def detect_compare_duplicates(source_infos: list[dict], compare_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    compare_by_size: dict[int, list[dict]] = {}
    for info in compare_infos:
        compare_by_size.setdefault(info["size"], []).append(info)

    items: list[ScanItem] = []
    total = max(len(source_infos), 1)
    for idx, src in enumerate(source_infos, start=1):
        candidates = compare_by_size.get(src["size"], [])
        if candidates:
            src_hash = get_hash(src)
            if src_hash:
                for cmp_info in candidates:
                    if src_hash == get_hash(cmp_info):
                        items.append(_make_item(
                            "同一ファイル", "比較フォルダにも同じ中身があります", cmp_info["path"], src["path"], "フォルダ比較",
                            src["size"], cmp_info["size"], src["mtime"], cmp_info["mtime"], "内容は完全一致です", "高", 1.0,
                            "対象側・比較側のどちらを処理するかを個別に選択できます。"
                        ))
                        break
        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "対象フォルダと比較フォルダの完全一致を確認中")
    return items




def detect_same_name_same_size(source_infos: list[dict], compare_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    compare_by_name_size: dict[tuple[str, str, int], list[dict]] = {}
    for info in compare_infos:
        compare_by_name_size.setdefault((info["name"].lower(), info["suffix"], info["size"]), []).append(info)

    items: list[ScanItem] = []
    total = max(len(source_infos), 1)
    for idx, src in enumerate(source_infos, start=1):
        key = (src["name"].lower(), src["suffix"], src["size"])
        for cmp_info in compare_by_name_size.get(key, []):
            src_hash = get_hash(src)
            cmp_hash = get_hash(cmp_info)
            if src_hash and cmp_hash and src_hash == cmp_hash:
                continue
            similarity = 0.0
            diff_summary = "サイズは同じですが内容が異なる可能性があります"
            if src["suffix"] in TEXT_COMPARE_EXTS:
                similarity, diff_summary = text_similarity_info(src, cmp_info)
            items.append(_make_item(
                "同名・同サイズ", shorten_reason("名前とサイズは同じですが内容が異なります", similarity), cmp_info["path"], src["path"], "フォルダ比較",
                src["size"], cmp_info["size"], src["mtime"], cmp_info["mtime"], diff_summary, "中" if similarity >= 0.5 else "低",
                similarity, "同名・同サイズだが別内容の可能性があるため、更新方向を確認して選んでください。"
            ))
            break
        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "同名・同サイズ候補を確認中")
    return items

def detect_same_name_different_content(source_infos: list[dict], compare_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    compare_by_name: dict[tuple[str, str], list[dict]] = {}
    for info in compare_infos:
        compare_by_name.setdefault((info["name"].lower(), info["suffix"]), []).append(info)

    items: list[ScanItem] = []
    total = max(len(source_infos), 1)
    for idx, src in enumerate(source_infos, start=1):
        key = (src["name"].lower(), src["suffix"])
        for cmp_info in compare_by_name.get(key, []):
            same_size = src["size"] == cmp_info["size"]
            if same_size:
                src_hash = get_hash(src)
                cmp_hash = get_hash(cmp_info)
                if src_hash and cmp_hash and src_hash == cmp_hash:
                    continue

            similarity = 0.0
            diff_summary = "本文比較対象外です"
            if src["suffix"] in TEXT_COMPARE_EXTS:
                similarity, diff_summary = text_similarity_info(src, cmp_info)

            if src["size"] > cmp_info["size"]:
                category = "同名・別内容（対象側が大きい）"
                reason = "同じ名前で内容が異なり、対象側ファイルの方が大きいです"
                note = "対象側ファイルの方が大きいため、どちらを残すか確認して更新方向を選んでください。"
            elif src["size"] < cmp_info["size"]:
                category = "同名・別内容（比較側が大きい）"
                reason = "同じ名前で内容が異なり、比較側ファイルの方が大きいです"
                note = "比較側ファイルの方が大きいため、どちらを残すか確認して更新方向を選んでください。"
            else:
                category = "同名・別内容（同サイズ）"
                reason = "同じ名前で内容が異なります"
                note = "サイズは同じですが内容が異なるため、更新方向を確認して選んでください。"

            items.append(_make_item(
                category, shorten_reason(reason, similarity), cmp_info["path"], src["path"], "フォルダ比較",
                src["size"], cmp_info["size"], src["mtime"], cmp_info["mtime"], diff_summary,
                "低" if similarity < 0.5 else "中", similarity, note
            ))
            break

        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "同名・別内容候補を確認中")
    return items

def detect_size_difference_candidates(source_infos: list[dict], compare_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    by_name: dict[tuple[str, str], list[dict]] = {}
    for info in compare_infos:
        by_name.setdefault((info["normalized"], info["suffix"]), []).append(info)

    items: list[ScanItem] = []
    total = max(len(source_infos), 1)
    for idx, src in enumerate(source_infos, start=1):
        key = (src["normalized"], src["suffix"])
        if src["suffix"] and not (src["looks_like_series_only"] and not src["has_version_word"]):
            for cmp_info in by_name.get(key, []):
                if src["path"] == cmp_info["path"] or src["size"] == cmp_info["size"]:
                    continue
                similarity = 0.0
                diff_summary = "本文比較対象外です"
                if src["suffix"] in TEXT_COMPARE_EXTS:
                    similarity, diff_summary = text_similarity_info(src, cmp_info)
                confidence = "低"
                if similarity >= 0.85:
                    confidence = "高"
                elif similarity >= 0.55:
                    confidence = "中"
                items.append(_make_item(
                    "サイズ差分候補", shorten_reason("名前は近いですがサイズが異なります", similarity), cmp_info["path"], src["path"], "フォルダ比較",
                    src["size"], cmp_info["size"], src["mtime"], cmp_info["mtime"], diff_summary, confidence, similarity,
                    "対象側・比較側のどちらで更新するかを選べます。"
                ))
                break
        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "サイズ差分候補を確認中")
    return items


def detect_update_candidates(source_infos: list[dict], compare_infos: list[dict], progress_cb=None, base_done: int = 0, total_work: int = 1) -> list[ScanItem]:
    by_name: dict[tuple[str, str], list[dict]] = {}
    for info in compare_infos:
        by_name.setdefault((info["normalized"], info["suffix"]), []).append(info)

    items: list[ScanItem] = []
    total = max(len(source_infos), 1)
    for idx, src in enumerate(source_infos, start=1):
        key = (src["normalized"], src["suffix"])
        candidates = by_name.get(key, [])
        if candidates and src["suffix"] and not (src["looks_like_series_only"] and not src["has_version_word"]):
            for cmp_info in candidates:
                if src["path"] == cmp_info["path"]:
                    continue
                newer = cmp_info["mtime"] > src["mtime"]
                version_hint = cmp_info["has_version_word"] or (
                    not cmp_info["looks_like_series_only"] and re.search(r"\b(v|ver|rev)\s*\d+\b", cmp_info["stem"], flags=re.I)
                )
                if not newer:
                    continue
                similarity = 0.0
                diff_summary = "本文比較対象外です"
                if src["suffix"] in TEXT_COMPARE_EXTS:
                    similarity, diff_summary = text_similarity_info(src, cmp_info)
                if version_hint or similarity >= 0.55 or src["normalized"] == cmp_info["normalized"]:
                    confidence = "低"
                    if version_hint and similarity >= 0.75:
                        confidence = "高"
                    elif version_hint or similarity >= 0.55:
                        confidence = "中"
                    items.append(_make_item(
                        "更新候補", shorten_reason("名前が近く、比較フォルダ側の方が新しい可能性があります", similarity), cmp_info["path"], src["path"], "フォルダ比較",
                        src["size"], cmp_info["size"], src["mtime"], cmp_info["mtime"], diff_summary, confidence, similarity,
                        "対象側・比較側のどちらで更新するかを選べます。"
                    ))
                    break
        if progress_cb and (idx == 1 or idx == total or idx % 100 == 0):
            progress_cb(base_done + idx, total_work, "更新候補を確認中")
    return items


def scan_folders(source_dir: str, compare_dir: str | None, exclude_dirs: list[str], exclude_exts: list[str], progress_cb: Callable[[int, int, str], None] | None = None) -> tuple[list[ScanItem], dict]:
    source_paths = iter_files(source_dir, exclude_dirs, exclude_exts)
    compare_paths = iter_files(compare_dir, exclude_dirs, exclude_exts) if compare_dir else []

    total_work = len(source_paths) + len(compare_paths)
    total_work += max(len(source_paths), 1)
    if compare_dir:
        total_work += max(len(source_infos := source_paths), 1) * 4  # placeholder length use
    # fix total without side effect
    total_work = len(source_paths) + len(compare_paths) + max(len(source_paths), 1) + (max(len(source_paths), 1) * 5 if compare_dir else 0)

    done = 0
    source_infos = build_file_info(source_paths, progress_cb=progress_cb, base_done=done, total_work=total_work)
    done += len(source_paths)
    compare_infos: list[dict] = []
    if compare_dir:
        compare_infos = build_file_info(compare_paths, progress_cb=progress_cb, base_done=done, total_work=total_work)
        done += len(compare_paths)

    items: list[ScanItem] = []
    items.extend(detect_inside_duplicates(source_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
    done += max(len(source_infos), 1)

    if compare_dir:
        items.extend(detect_compare_duplicates(source_infos, compare_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
        done += max(len(source_infos), 1)

        items.extend(detect_same_name_same_size(source_infos, compare_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
        done += max(len(source_infos), 1)

        items.extend(detect_same_name_different_content(source_infos, compare_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
        done += max(len(source_infos), 1)

        items.extend(detect_size_difference_candidates(source_infos, compare_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
        done += max(len(source_infos), 1)

        items.extend(detect_update_candidates(source_infos, compare_infos, progress_cb=progress_cb, base_done=done, total_work=total_work))
        done += max(len(source_infos), 1)

    if progress_cb:
        progress_cb(total_work, total_work, "スキャン結果を整理中")

    source_special = summarize_special_counts(source_infos)
    compare_special = summarize_special_counts(compare_infos)
    summary = {
        "source_files": len(source_infos),
        "compare_files": len(compare_infos),
        "source_image_files": source_special["image_files"],
        "compare_image_files": compare_special["image_files"],
        "source_zip_files": source_special["zip_files"],
        "compare_zip_files": compare_special["zip_files"],
        "source_zip_image_files": source_special["zip_image_files"],
        "compare_zip_image_files": compare_special["zip_image_files"],
        "file_count_winner": "対象フォルダ" if len(source_infos) > len(compare_infos) else ("比較フォルダ" if len(source_infos) < len(compare_infos) else "同数"),
        "source_bytes": sum(max(0, x.get("size", 0)) for x in source_infos),
        "compare_bytes": sum(max(0, x.get("size", 0)) for x in compare_infos),
        "same_items": sum(1 for x in items if x.category == "同一ファイル"),
        "update_items": sum(1 for x in items if x.category == "更新候補"),
        "same_name_same_size_items": sum(1 for x in items if x.category == "同名・同サイズ"),
        "same_name_diff_target_large_items": sum(1 for x in items if x.category == "同名・別内容（対象側が大きい）"),
        "same_name_diff_compare_large_items": sum(1 for x in items if x.category == "同名・別内容（比較側が大きい）"),
        "same_name_diff_same_size_items": sum(1 for x in items if x.category == "同名・別内容（同サイズ）"),
        "size_diff_items": sum(1 for x in items if x.category == "サイズ差分候補"),
        "total_items": len(items),
    }
    return items, summary
