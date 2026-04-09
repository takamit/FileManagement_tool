from __future__ import annotations
from pathlib import Path

def _read_txt(path: Path, max_chars: int) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "latin-1"):
        try:
            return path.read_text(encoding=enc, errors="ignore")[:max_chars]
        except Exception:
            pass
    return "(テキストを読み取れませんでした)"

def _read_docx(path: Path, max_chars: int) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
        return text[:max_chars] if text else "(本文が空です)"
    except Exception as e:
        return f"(DOCX読み取り不可: {e})"

def _read_pdf(path: Path, max_chars: int) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages[:20]:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                pass
        text = "\n".join(parts).strip()
        return text[:max_chars] if text else "(PDF本文を抽出できませんでした)"
    except Exception as e:
        return f"(PDF読み取り不可: {e})"

def read_text_preview(file_path: str, max_chars: int = 3000) -> str:
    path = Path(file_path)
    if not path.exists():
        return "(ファイルが見つかりません)"
    ext = path.suffix.lower()
    if ext in {".txt",".md",".csv",".json",".py",".log",".ini",".yaml",".yml"}:
        return _read_txt(path, max_chars)
    if ext == ".docx":
        return _read_docx(path, max_chars)
    if ext == ".pdf":
        return _read_pdf(path, max_chars)
    return "(本文プレビュー対象外の形式です)"
