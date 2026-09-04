#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

IGNORED_DIR_NAMES = {
    ".git", ".github", ".idea", ".vscode", ".venv", "venv",
    "__pycache__", "node_modules", "images",
}
IGNORED_FILE_NAMES = {
    "README.md", ".gitkeep", ".DS_Store", "Thumbs.db", "images_manifest.txt",
}
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".bmp", ".tif", ".tiff", ".ico",
}
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
GENERIC_H1 = {
    "рабочая программа", "рабочая программа профессионального модуля",
    "фонд оценочных средств", "фос", "readme",
}

# Только для красивых названий уже известных документов.
# На обнаружение папок/файлов эти правила не влияют.
TITLE_OVERRIDES = {
    "РПД/РП_МДК0201_МПС_КСК_2025.md":
        "МДК.02.01 «Микропроцессорные системы» — 3 курс",
    "РПД/РП_МДК0201_Микропроцессорные_системы_4_курс_КСК_2025.md":
        "МДК.02.01 «Микропроцессорные системы» — 4 курс",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_КСК_2025.md":
        "МДК.02.02 «Программирование микроконтроллеров» — 3 курс",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_4_курс_КСК_2025.md":
        "МДК.02.02 «Программирование микроконтроллеров» — 4 курс",
    "ФОС/Входной_контроль_МПС_и_программирование_МК_3_курс.md":
        "Входной контроль по МПС и программированию микроконтроллеров — 3 курс",
}

@dataclass(frozen=True)
class Item:
    abs_path: Path
    rel: str
    kind: str          # dir | markdown | file
    title: str
    parent_rel: str
    depth: int

def natural_key(text: str):
    return [int(x) if x.isdigit() else x.casefold()
            for x in re.split(r"(\d+)", text)]

def sanitize_page_id(text: str) -> str:
    text = text.strip().replace("_", "-").replace(" ", "-")
    text = re.sub(r'[\\/:*?"<>|#]+', "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-.")

def encode_path(rel: str) -> str:
    return "/".join(quote(part, safe="-_.~") for part in PurePosixPath(rel).parts)

def md_escape(text: str) -> str:
    return (str(text).replace("\\", "\\\\").replace("[", "\\[")
            .replace("]", "\\]").replace("|", "\\|"))

def humanize_name(name: str) -> str:
    stem = Path(name).stem.replace("_", " ")
    return re.sub(r"\s+", " ", stem).strip() or name

def read_markdown(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

def first_h1(path: Path) -> str | None:
    if path.suffix.casefold() not in MARKDOWN_EXTENSIONS:
        return None
    text = read_markdown(path)
    if text is None:
        return None
    for line in text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            value = re.sub(r"[*_`]+", "", m.group(1)).strip()
            return value or None
    return None

def directory_readme(path: Path) -> Path | None:
    for name in ("README.md", "readme.md", "Readme.md"):
        p = path / name
        if p.is_file():
            return p
    return None

def directory_title(path: Path) -> str:
    readme = directory_readme(path)
    if readme:
        title = first_h1(readme)
        if title and title.casefold() not in GENERIC_H1:
            return title
    return humanize_name(path.name)

def material_title(path: Path, rel: str) -> str:
    if rel in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[rel]
    title = first_h1(path)
    if title and title.casefold() not in GENERIC_H1:
        return title
    return humanize_name(path.name)

def _ignored_dir_name(name: str) -> bool:
    return name.casefold() in {x.casefold() for x in IGNORED_DIR_NAMES}

def _ignored_file(path: Path, repo_root: Path) -> bool:
    if path.resolve() == (repo_root / "README.md").resolve():
        return True
    if path.name.casefold() in {x.casefold() for x in IGNORED_FILE_NAMES}:
        return True
    if path.suffix.casefold() in IMAGE_EXTENSIONS:
        return True
    rel_parts = path.relative_to(repo_root).parts[:-1]
    return any(_ignored_dir_name(part) for part in rel_parts)

def discover(repo_root: Path) -> list[Item]:
    repo_root = repo_root.resolve()
    result: list[Item] = []

    def walk(folder: Path, parent_rel: str, depth: int) -> None:
        for entry in sorted(folder.iterdir(), key=lambda p: natural_key(p.name)):
            if entry.is_dir():
                if _ignored_dir_name(entry.name):
                    continue
                rel = entry.relative_to(repo_root).as_posix()
                result.append(Item(
                    entry, rel, "dir", directory_title(entry), parent_rel, depth
                ))
                walk(entry, rel, depth + 1)
            elif entry.is_file():
                if _ignored_file(entry, repo_root):
                    continue
                rel = entry.relative_to(repo_root).as_posix()
                kind = ("markdown" if entry.suffix.casefold() in MARKDOWN_EXTENSIONS
                        else "file")
                result.append(Item(
                    entry, rel, kind, material_title(entry, rel), parent_rel, depth
                ))
    walk(repo_root, "", 0)
    return result

def children(items: list[Item], parent_rel: str) -> list[Item]:
    return sorted(
        [x for x in items if x.parent_rel == parent_rel],
        key=lambda x: (0 if x.kind == "dir" else 1, natural_key(x.rel)),
    )

def top_level_dirs(items: list[Item]) -> list[Item]:
    return [x for x in children(items, "") if x.kind == "dir"]

def top_level_files(items: list[Item]) -> list[Item]:
    return [x for x in children(items, "") if x.kind != "dir"]

def repo_blob_url(owner: str, repo: str, branch: str, rel: str) -> str:
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{encode_path(rel)}"

def repo_tree_url(owner: str, repo: str, branch: str, rel: str) -> str:
    return f"https://github.com/{owner}/{repo}/tree/{branch}/{encode_path(rel)}"

def repo_raw_url(owner: str, repo: str, branch: str, rel: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encode_path(rel)}"

def relative_repo_link(rel: str) -> str:
    return "./" + encode_path(rel)

def dir_page_id(rel: str) -> str:
    return sanitize_page_id(rel)

def markdown_page_id(rel: str) -> str:
    path = PurePosixPath(rel)
    parts = list(path.parts)
    stem = path.stem
    if len(parts) >= 2 and (
        sanitize_page_id(parts[-2]).casefold()
        == sanitize_page_id(stem).casefold()
    ):
        parts = parts[:-1]
    else:
        parts[-1] = stem
    return sanitize_page_id("-".join(parts))
