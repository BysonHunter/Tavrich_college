#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

from repo_catalog import (
    Item, children, dir_page_id, directory_readme, discover,
    markdown_page_id, md_escape, read_markdown, repo_blob_url,
    repo_raw_url, repo_tree_url, top_level_dirs, top_level_files,
)

def md_link(label: str, page_id: str) -> str:
    return f"[{md_escape(label)}]({page_id})"

def clean_wiki(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for item in wiki_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

def write(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")

def resolve_relative(source_rel: str, target: str) -> str | None:
    target = target.strip()
    if not target or target.startswith(
        ("#", "http://", "https://", "mailto:", "data:", "//")
    ):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = unquote(target.split("#", 1)[0])
    base = PurePosixPath(source_rel).parent
    return os.path.normpath((base / target).as_posix()).replace("\\", "/")

def rewrite_markdown(text, source_rel, markdown_map, owner, repo, branch):
    image_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    def image_sub(m):
        resolved = resolve_relative(source_rel, m.group(2))
        if resolved is None:
            return m.group(0)
        return f"![{m.group(1)}]({repo_raw_url(owner, repo, branch, resolved)})"
    text = image_re.sub(image_sub, text)

    html_re = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.I)
    def html_sub(m):
        resolved = resolve_relative(source_rel, m.group(2))
        if resolved is None:
            return m.group(0)
        return m.group(1) + repo_raw_url(owner, repo, branch, resolved) + m.group(3)
    text = html_re.sub(html_sub, text)

    link_re = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
    def link_sub(m):
        label, target = m.group(1), m.group(2).strip()
        if target.startswith(("#", "http://", "https://", "mailto:", "//")):
            return m.group(0)

        if "#" in target:
            target_path, anchor = target.split("#", 1)
            anchor = "#" + anchor
        else:
            target_path, anchor = target, ""

        resolved = resolve_relative(source_rel, target_path)
        if resolved is None:
            return m.group(0)

        if resolved in markdown_map:
            return md_link(label, markdown_map[resolved] + anchor)

        return f"[{label}]({repo_blob_url(owner, repo, branch, resolved)}{anchor})"

    return link_re.sub(link_sub, text)

def directory_intro(directory: Item, source_root: Path, markdown_map,
                    owner, repo, branch) -> str | None:
    readme = directory_readme(directory.abs_path)
    if not readme:
        return None
    text = read_markdown(readme)
    if not text:
        return None

    rel = readme.relative_to(source_root).as_posix()
    text = rewrite_markdown(text, rel, markdown_map, owner, repo, branch)
    text = re.sub(r"^\s*#\s+.+?\n+", "", text, count=1, flags=re.MULTILINE).strip()
    return text or None

def build_dir_page(directory: Item, source_root: Path, items, markdown_map,
                   owner, repo, branch) -> str:
    parent_id = "Home" if not directory.parent_rel else dir_page_id(directory.parent_rel)
    lines = [
        f"# {directory.title}", "",
        f"[🏠 Главная](Home) · {md_link('← Назад', parent_id)}", "",
        f"> **Папка в основном репозитории:** "
        f"[{directory.rel}]({repo_tree_url(owner, repo, branch, directory.rel)})", "",
    ]

    intro = directory_intro(
        directory, source_root, markdown_map, owner, repo, branch
    )
    if intro:
        lines += ["## Описание раздела", "", intro, ""]

    kids = children(items, directory.rel)
    subdirs = [x for x in kids if x.kind == "dir"]
    markdowns = [x for x in kids if x.kind == "markdown"]
    files = [x for x in kids if x.kind == "file"]

    if subdirs:
        lines += ["## Подразделы", ""]
        for x in subdirs:
            lines.append(f"- {md_link(x.title, dir_page_id(x.rel))}")
        lines.append("")

    if markdowns:
        lines += ["## Материалы", ""]
        for x in markdowns:
            lines.append(f"- {md_link(x.title, markdown_map[x.rel])}")
        lines.append("")

    if files:
        lines += ["## Файлы", ""]
        for x in files:
            lines.append(
                f"- [{md_escape(x.title)}]({repo_blob_url(owner, repo, branch, x.rel)})"
            )
        lines.append("")

    if not kids:
        lines += ["_Нет опубликованных материалов._", ""]

    return "\n".join(lines)

def build_markdown_page(item: Item, markdown_map, owner, repo, branch) -> str:
    text = read_markdown(item.abs_path) or ""
    text = rewrite_markdown(text, item.rel, markdown_map, owner, repo, branch)
    parent_id = dir_page_id(item.parent_rel) if item.parent_rel else "Home"

    return (
        f"[🏠 Главная](Home) · {md_link('← К разделу', parent_id)}\n\n"
        f"> **Источник:** [{item.rel}]"
        f"({repo_blob_url(owner, repo, branch, item.rel)})  \n"
        f"> Автосинхронизация из ветки `{branch}`.\n\n"
        "---\n\n" + text.lstrip()
    )

def build_home(items, owner, repo, branch) -> str:
    lines = [
        "# Учебно-методические материалы Таврического колледжа", "",
        "Wiki формируется автоматически по фактической структуре основного репозитория.", "",
        "## Разделы", "",
    ]
    for root in top_level_dirs(items):
        lines.append(f"- {md_link(root.title, dir_page_id(root.rel))}")

    root_files = top_level_files(items)
    if root_files:
        lines += ["", "## Файлы в корне", ""]
        for x in root_files:
            if x.kind == "markdown":
                lines.append(f"- {md_link(x.title, markdown_page_id(x.rel))}")
            else:
                lines.append(
                    f"- [{md_escape(x.title)}]({repo_blob_url(owner, repo, branch, x.rel)})"
                )

    lines += [
        "", "---", "",
        f"[Основной репозиторий](https://github.com/{owner}/{repo})", "",
        "> Новые каталоги и материалы автоматически появляются после `git push`; "
        "удалённые — исчезают.",
    ]
    return "\n".join(lines)

def sidebar_branch(directory: Item, items, level: int) -> list[str]:
    if level > 4:
        return []
    indent = "  " * max(level - 1, 0)
    lines = [f"{indent}- {md_link(directory.title, dir_page_id(directory.rel))}"]
    for child in [x for x in children(items, directory.rel) if x.kind == "dir"]:
        lines.extend(sidebar_branch(child, items, level + 1))
    return lines

def build_sidebar(items, owner, repo) -> str:
    lines = ["## 🏠 Навигация", "", "[Главная](Home)", "", "---", ""]
    for root in top_level_dirs(items):
        lines.extend(sidebar_branch(root, items, 1))
    lines += [
        "", "---", "",
        f"[Основной репозиторий](https://github.com/{owner}/{repo})",
    ]
    return "\n".join(lines)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--wiki", required=True)
    p.add_argument("--owner", default="BysonHunter")
    p.add_argument("--repo", default="Tavrich_college")
    p.add_argument("--branch", default="main")
    args = p.parse_args()

    source = Path(args.source).resolve()
    wiki_dir = Path(args.wiki).resolve()
    items = discover(source)
    markdowns = [x for x in items if x.kind == "markdown"]
    markdown_map = {x.rel: markdown_page_id(x.rel) for x in markdowns}

    clean_wiki(wiki_dir)

    write(wiki_dir / "Home.md", build_home(items, args.owner, args.repo, args.branch))
    write(wiki_dir / "_Sidebar.md", build_sidebar(items, args.owner, args.repo))
    write(
        wiki_dir / "_Footer.md",
        "---\n"
        "**09.02.01 «Компьютерные системы и комплексы»** · "
        f"[Основной репозиторий](https://github.com/{args.owner}/{args.repo}) · "
        f"автосинхронизация из `{args.branch}`",
    )

    for directory in [x for x in items if x.kind == "dir"]:
        write(
            wiki_dir / f"{dir_page_id(directory.rel)}.md",
            build_dir_page(
                directory, source, items, markdown_map,
                args.owner, args.repo, args.branch,
            ),
        )

    for item in markdowns:
        write(
            wiki_dir / f"{markdown_map[item.rel]}.md",
            build_markdown_page(
                item, markdown_map, args.owner, args.repo, args.branch
            ),
        )

    print(f"Wiki каталогов: {len([x for x in items if x.kind == 'dir'])}")
    print(f"Markdown-страниц: {len(markdowns)}")
    print(f"Файлов-ссылок: {len([x for x in items if x.kind == 'file'])}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
