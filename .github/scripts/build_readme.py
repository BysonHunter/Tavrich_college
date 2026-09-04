#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path

from repo_catalog import (
    Item, children, discover, md_escape, relative_repo_link,
    top_level_dirs, top_level_files,
)

def item_link(item: Item) -> str:
    return f"[{md_escape(item.title)}]({relative_repo_link(item.rel)})"

def build_tree(items: list[Item]) -> str:
    lines = ["Tavrich_college/", "│", "├── README.md"]
    roots = top_level_dirs(items)
    root_files = top_level_files(items)

    for i, root in enumerate(roots):
        last = i == len(roots) - 1 and not root_files
        marker = "└── " if last else "├── "
        prefix = "    " if last else "│   "
        lines.append(f"{marker}{Path(root.rel).name}/")
        add_tree_children(items, root.rel, lines, prefix)

    for i, item in enumerate(root_files):
        marker = "└── " if i == len(root_files) - 1 else "├── "
        lines.append(f"{marker}{Path(item.rel).name}")

    return "\n".join(lines)

def add_tree_children(items, parent_rel, lines, prefix):
    kids = children(items, parent_rel)
    for i, item in enumerate(kids):
        last = i == len(kids) - 1
        marker = "└── " if last else "├── "
        next_prefix = prefix + ("    " if last else "│   ")
        name = Path(item.rel).name
        if item.kind == "dir":
            lines.append(f"{prefix}{marker}{name}/")
            add_tree_children(items, item.rel, lines, next_prefix)
        else:
            lines.append(f"{prefix}{marker}{name}")

def render_dir(items: list[Item], directory: Item, level: int = 2) -> list[str]:
    level = min(level, 6)
    lines = [
        f"{'#' * level} {directory.title}", "",
        f"Папка: [{directory.rel}]({relative_repo_link(directory.rel + '/')})", "",
    ]
    kids = children(items, directory.rel)
    files = [x for x in kids if x.kind != "dir"]
    dirs = [x for x in kids if x.kind == "dir"]

    for item in files:
        lines.append(f"- {item_link(item)}")
    if files:
        lines.append("")

    for subdir in dirs:
        lines.extend(render_dir(items, subdir, level + 1))

    if not kids:
        lines += ["_Нет опубликованных материалов._", ""]
    return lines

def build(repo: Path) -> str:
    items = discover(repo)
    roots = top_level_dirs(items)
    root_files = top_level_files(items)

    file_count = len([x for x in items if x.kind != "dir"])
    dir_count = len([x for x in items if x.kind == "dir"])

    lines = [
        "# Tavrich College — учебно-методические материалы", "",
        "Репозиторий содержит учебно-методические материалы Таврического колледжа "
        "для специальности **09.02.01 «Компьютерные системы и комплексы»**.", "",
        "> `README.md` формируется автоматически по фактической структуре репозитория. "
        "Новые каталоги и материалы появляются после `git push`, удалённые — исчезают.", "",
        "> Технические каталоги (`.git`, `.github`, `images`, `.vscode`, `.idea`, "
        "`__pycache__`, виртуальные окружения и `node_modules`) в учебную навигацию "
        "не включаются.", "",
        "---", "", "## Содержание", "",
        "1. [Структура репозитория](#section-1)",
    ]

    section = 2
    for root in roots:
        lines.append(f"{section}. [{root.title}](#section-{section})")
        section += 1

    if root_files:
        lines.append(f"{section}. [Файлы в корне](#section-{section})")
        section += 1

    lines.append(f"{section}. [Как работает автоматизация](#section-{section})")

    lines += [
        "", "---", "", '<a id="section-1"></a>',
        "# 1. Структура репозитория", "",
        "```text", build_tree(items), "```", "",
        f"Автоматически обнаружено каталогов: **{dir_count}**; "
        f"файлов материалов: **{file_count}**.", "",
        "[↑ К содержанию](#содержание)",
    ]

    section = 2
    for root in roots:
        lines += [
            "", "---", "", f'<a id="section-{section}"></a>',
            f"# {section}. {root.title}", "",
            f"Папка: [{root.rel}]({relative_repo_link(root.rel + '/')})", "",
        ]
        direct_files = [x for x in children(items, root.rel) if x.kind != "dir"]
        for item in direct_files:
            lines.append(f"- {item_link(item)}")
        if direct_files:
            lines.append("")

        for subdir in [x for x in children(items, root.rel) if x.kind == "dir"]:
            lines.extend(render_dir(items, subdir, 2))

        lines += ["[↑ К содержанию](#содержание)"]
        section += 1

    if root_files:
        lines += [
            "", "---", "", f'<a id="section-{section}"></a>',
            f"# {section}. Файлы в корне", "",
        ]
        for item in root_files:
            lines.append(f"- {item_link(item)}")
        lines += ["", "[↑ К содержанию](#содержание)"]
        section += 1

    lines += [
        "", "---", "", f'<a id="section-{section}"></a>',
        f"# {section}. Как работает автоматизация", "",
        "После изменения структуры или материалов достаточно обычного `git push`.", "",
        "```text",
        "изменение репозитория",
        "        ↓",
        "     git push",
        "        ↓",
        "GitHub Actions",
        "   ├── Update README",
        "   └── Update GitHub Wiki",
        "```", "",
        "Пустые папки Git не хранит. Если нужен пустой каталог, добавьте в него "
        "`.gitkeep`; сам `.gitkeep` в навигации показываться не будет.", "",
        "[GitHub Wiki](../../wiki)", "",
        "---", "",
        "**Специальность:** 09.02.01 «Компьютерные системы и комплексы»  ",
        "**Учебные материалы Таврического колледжа**", "",
    ]
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output", default="README.md")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    output = repo / args.output
    output.write_text(build(repo), encoding="utf-8")

    items = discover(repo)
    print(f"README создан: {output}")
    print(f"Каталогов: {len([x for x in items if x.kind == 'dir'])}")
    print(f"Файлов: {len([x for x in items if x.kind != 'dir'])}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
