#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote

ROOTS = ("АккМон", "РПД", "ФОС", "МПС", "ПМК")
SUBJECTS = ("МПС", "ПМК")
IMAGE_EXTS = {".png",".jpg",".jpeg",".gif",".webp",".svg",".bmp",".tif",".tiff",".ico"}

TITLE_OVERRIDES = {
    "РПД/РП_МДК0201_МПС_КСК_2025.md": "МДК.02.01 «Микропроцессорные системы» — 3 курс",
    "РПД/РП_МДК0201_Микропроцессорные_системы_4_курс_КСК_2025.md": "МДК.02.01 «Микропроцессорные системы» — 4 курс",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_КСК_2025.md": "МДК.02.02 «Программирование микроконтроллеров» — 3 курс",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_4_курс_КСК_2025.md": "МДК.02.02 «Программирование микроконтроллеров» — 4 курс",
    "ФОС/Входной_контроль_МПС_и_программирование_МК_3_курс.md": "Входной контроль по МПС и программированию микроконтроллеров — 3 курс",
    "АккМон/Вопросы_к_аккредитации_Микропроцессорные_системы.md": "Вопросы к аккредитации — микропроцессорные системы",
    "АккМон/Вопросы_к_аккредитации_Программирование_микроконтроллеров_11-09-2026.md": "Вопросы к аккредитации — программирование микроконтроллеров",
    "АккМон/ФОС_Микропроцессорные_системы_09.02.01.md": "ФОС — микропроцессорные системы, 3 курс",
    "АккМон/ФОС_Микропроцессорные_системы_4_курс_09.02.01.md": "ФОС — микропроцессорные системы, 4 курс",
    "АккМон/ФОС_Программирование_микроконтроллеров_09.02.01.md": "ФОС — программирование микроконтроллеров, 3 курс",
    "АккМон/ФОС_Программирование_микроконтроллеров_4_курс_09.02.01.md": "ФОС — программирование микроконтроллеров, 4 курс",
}

@dataclass(frozen=True)
class Material:
    rel: str
    root: str
    course: str | None
    category: str | None
    title: str

def natural_key(s: str):
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r"(\d+)", s)]

def md_escape(s: str) -> str:
    return s.replace("\\","\\\\").replace("[","\\[").replace("]","\\]").replace("|","\\|")

def enc(rel: str) -> str:
    return "/".join(quote(p, safe="-_.~") for p in PurePosixPath(rel).parts)

def link(rel: str, label: str) -> str:
    return f"[{md_escape(label)}](./{enc(rel)})"

def h1(path: Path) -> str | None:
    if path.suffix.casefold() != ".md":
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    for line in text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return re.sub(r"[*_`]+","",m.group(1)).strip()
    return None

def detect_course(parts: tuple[str,...]):
    for i, p in enumerate(parts):
        m = re.fullmatch(r"(\d+)\s*курс", p, re.I)
        if m:
            return f"{int(m.group(1))} курс", i
    return None, None

def title_for(path: Path, rel: str) -> str:
    if rel in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[rel]
    title = h1(path)
    if title and title.casefold() not in {"рабочая программа","фонд оценочных средств","фос"}:
        return title
    return re.sub(r"\s+"," ",path.stem.replace("_"," ")).strip()

def discover(repo: Path) -> list[Material]:
    out = []
    for root in ROOTS:
        base = repo / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.name.casefold() == "readme.md":
                continue
            if p.suffix.casefold() in IMAGE_EXTS:
                continue
            if any(part.casefold() == "images" for part in p.parts):
                continue
            rel = p.relative_to(repo).as_posix()
            parts = PurePosixPath(rel).parts
            course, idx = detect_course(parts)
            category = None
            if root in SUBJECTS and course:
                category = parts[idx+1] if idx+1 < len(parts)-1 else "Материалы"
            out.append(Material(rel, root, course, category, title_for(p, rel)))
    return sorted(out, key=lambda m: natural_key(m.rel))

def category_key(c: str):
    cl = c.casefold()
    if cl == "лекции": return (0, natural_key(c))
    if "практи" in cl or "лаборатор" in cl: return (1, natural_key(c))
    return (2, natural_key(c))

def folder_link(rel: str, label: str | None = None):
    rel = rel.rstrip("/") + "/"
    return f"[{md_escape(label or rel.rstrip('/'))}](./{enc(rel)})"

def tree(repo: Path) -> str:
    lines = ["Tavrich_college/","│","├── README.md"]
    roots = [r for r in ROOTS if (repo/r).exists()]
    for ri, root in enumerate(roots):
        last_root = ri == len(roots)-1
        lines.append(("└── " if last_root else "├── ") + root + "/")
        add_children(repo/root, lines, "    " if last_root else "│   ", 0, 4)
    return "\n".join(lines)

def add_children(folder: Path, lines: list[str], prefix: str, depth: int, max_depth: int):
    if depth >= max_depth:
        return
    entries = []
    for p in sorted(folder.iterdir(), key=lambda x: natural_key(x.name)):
        if p.name.casefold() in {"images","readme.md"}:
            continue
        if p.is_file() and p.suffix.casefold() in IMAGE_EXTS:
            continue
        entries.append(p)
    for i,p in enumerate(entries):
        last = i == len(entries)-1
        mark = "└── " if last else "├── "
        lines.append(prefix + mark + p.name + ("/" if p.is_dir() else ""))
        if p.is_dir():
            add_children(p, lines, prefix + ("    " if last else "│   "), depth+1, max_depth)

def docs_section(n: int, root: str, name: str, intro: str, mats: list[Material]) -> str:
    items = [m for m in mats if m.root == root]
    lines = [f"# {n}. `{root}` — {name}","",intro,""]
    if not items:
        return "\n".join(lines + ["_Материалы отсутствуют._"])
    lines += ["| Материал | Файл |","|---|---|"]
    for m in items:
        lines.append(f"| {link(m.rel,m.title)} | `{md_escape(m.rel)}` |")
    return "\n".join(lines)

def subject_section(n: int, root: str, name: str, mats: list[Material]) -> str:
    items = [m for m in mats if m.root == root]
    lines = [f"# {n}. `{root}` — {name}","",
             f"Папка {folder_link(root,root)} содержит учебные материалы по **{name}**.",""]
    courses = sorted({m.course for m in items if m.course}, key=natural_key)
    if not courses:
        return "\n".join(lines + ["_Материалы отсутствуют._"])
    for ci, course in enumerate(courses,1):
        lines += [f"## {n}.{ci}. {course}","",f"Папка: {folder_link(f'{root}/{course}',f'{root}/{course}')}",""]
        course_items = [m for m in items if m.course == course]
        cats = sorted({m.category or "Материалы" for m in course_items}, key=category_key)
        for cat in cats:
            cat_items = [m for m in course_items if (m.category or "Материалы")==cat]
            lines += [f"### {cat}",""]
            if cat != "Материалы" and cat_items:
                parts = PurePosixPath(cat_items[0].rel).parts
                if len(parts) >= 4:
                    cat_path = "/".join(parts[:3])
                    lines += [f"Папка: {folder_link(cat_path,cat_path)}",""]
            for m in cat_items:
                lines.append(f"- {link(m.rel,m.title)}")
            lines.append("")
    return "\n".join(lines).rstrip()

def build(repo: Path) -> str:
    mats = discover(repo)
    counts = {r:len([m for m in mats if m.root==r]) for r in ROOTS}
    total = sum(counts.values())
    lines = [
        "# Tavrich College — учебно-методические материалы","",
        "Репозиторий содержит учебно-методические материалы Таврического колледжа для специальности **09.02.01 «Компьютерные системы и комплексы»**.","",
        "Основные учебные направления:","",
        "- **МДК.02.01 «Микропроцессорные системы» (МПС)**;",
        "- **МДК.02.02 «Программирование микроконтроллеров» (ПМК)**.","",
        "> README формируется автоматически по фактическому содержимому репозитория. При добавлении, удалении или переименовании материалов навигация обновляется GitHub Actions.","",
        "> Каталоги `images` и графические файлы в README не перечисляются.","",
        "---","","## Содержание","",
        "1. [Структура репозитория](#1-структура-репозитория)",
        "2. [АккМон — аккредитационный мониторинг](#2-аккмон--аккредитационный-мониторинг)",
        "3. [РПД — рабочие программы дисциплин](#3-рпд--рабочие-программы-дисциплин)",
        "4. [ФОС — оценочные материалы](#4-фос--оценочные-материалы)",
        "5. [МПС — микропроцессорные системы](#5-мпс--микропроцессорные-системы)",
        "6. [ПМК — программирование микроконтроллеров](#6-пмк--программирование-микроконтроллеров)",
        "7. [Как пользоваться репозиторием](#7-как-пользоваться-репозиторием)","",
        "---","","# 1. Структура репозитория","","```text",tree(repo),"```","",
        f"Автоматически обнаружено материалов: **{total}**.","",
        "| Раздел | Количество файлов |","|---|---:|",
    ]
    for r in ROOTS:
        lines.append(f"| `{r}` | {counts[r]} |")
    lines += ["","[↑ К содержанию](#содержание)","","---","",
              docs_section(2,"АккМон","аккредитационный мониторинг","Банки вопросов и фонды оценочных средств для аккредитационного мониторинга.",mats),
              "","[↑ К содержанию](#содержание)","","---","",
              docs_section(3,"РПД","рабочие программы дисциплин","Рабочие программы МДК.02.01 и МДК.02.02.",mats),
              "","[↑ К содержанию](#содержание)","","---","",
              docs_section(4,"ФОС","оценочные материалы","Входной контроль и другие оценочные материалы.",mats),
              "","[↑ К содержанию](#содержание)","","---","",
              subject_section(5,"МПС","микропроцессорные системы",mats),
              "","[↑ К содержанию](#содержание)","","---","",
              subject_section(6,"ПМК","программирование микроконтроллеров",mats),
              "","[↑ К содержанию](#содержание)","","---","",
              "# 7. Как пользоваться репозиторием","",
              "1. Откройте рабочую программу в [`РПД`](./РПД/).",
              "2. Перейдите к [`МПС`](./МПС/) или [`ПМК`](./ПМК/).",
              "3. Выберите курс и тип материала: лекции, практические/лабораторные работы и другие разделы.",
              "4. Для контроля знаний используйте [`ФОС`](./ФОС/) и [`АккМон`](./АккМон/).",
              "5. Для последовательного просмотра материалов используйте [GitHub Wiki](../../wiki).","",
              "### Автоматическое обновление","",
              "`README.md` обновляется workflow `Update README` после изменений в учебных папках. Вручную поддерживать список материалов не требуется.","",
              "---","","**Специальность:** 09.02.01 «Компьютерные системы и комплексы»  ",
              "**Учебные материалы Таврического колледжа**",""]
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--output", default="README.md")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    text = build(repo)
    path = repo / args.output
    path.write_text(text, encoding="utf-8")
    mats = discover(repo)
    print(f"README создан: {path}")
    print(f"Материалов: {len(mats)}")
    for r in ROOTS:
        print(f"{r}: {len([m for m in mats if m.root==r])}")

if __name__ == "__main__":
    main()
