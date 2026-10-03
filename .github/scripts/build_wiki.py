#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, quote

from repo_catalog import (
    Item, children, dir_page_id, discover,
    markdown_page_id, md_escape, read_markdown, repo_blob_url,
    repo_raw_url, repo_tree_url, top_level_dirs, top_level_files,
)

def md_link(label: str, page_id: str) -> str:
    return f"[{md_escape(label)}]({quote(page_id, safe="-_.~#")})"

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

SUBJECTS = {
    "МПС": ("Микропроцессорные системы", "Архитектура микропроцессоров, адресация, ассемблер, шины и проектирование устройств."),
    "ПМК": ("Программирование микроконтроллеров", "Arduino, ARM Cortex-M, периферия, подключение устройств и отладка управляющих программ."),
}
DOCUMENTS = {
    "РПД": ("Рабочие программы", "Содержание дисциплин и тематическое планирование."),
    "ФОС": ("Контроль знаний", "Входной контроль и материалы для проверки знаний."),
    "АккМон": ("Аккредитация и оценочные материалы", "Вопросы к аккредитации и фонды оценочных средств."),
}

def section_title(item):
    name = Path(item.rel).name
    if name in SUBJECTS:
        return SUBJECTS[name][0]
    if name in DOCUMENTS:
        return DOCUMENTS[name][0]
    if name.startswith("Демоэкзамен"):
        return "Демонстрационный экзамен"
    return item.title

def material_title(item):
    if item.title.casefold() == "вопросы к аккредитации":
        return item.title + " — " + ("МПС" if "Микропроцессорные" in item.rel else "ПМК")
    return item.title

def descendants(items, rel):
    return [x for x in items if x.kind != "dir" and x.rel.startswith(rel + "/")]

def material_link(item, markdown_map, owner, repo, branch):
    if item.kind == "markdown":
        return md_link(material_title(item), markdown_map[item.rel])
    return f"[{md_escape(material_title(item))}]({repo_blob_url(owner, repo, branch, item.rel)})"

def material_table(materials, markdown_map, owner, repo, branch):
    if not materials:
        return ["_Материалы пока не опубликованы._", ""]
    lines = ["| Материал | Формат |", "| :--- | :---: |"]
    for item in materials:
        fmt = "Страница Wiki" if item.kind == "markdown" else item.abs_path.suffix.lstrip(".").upper() or "Файл"
        lines.append(f"| {material_link(item, markdown_map, owner, repo, branch)} | {fmt} |")
    return lines + [""]

def breadcrumbs(rel, items, current_id=None):
    by_rel = {x.rel: x for x in items if x.kind == "dir"}
    parts = [md_link("🏠 Главная", "Home")]
    for parent in reversed(PurePosixPath(rel).parents):
        key = parent.as_posix()
        if key in by_rel and dir_page_id(key) != current_id:
            parts.append(md_link(section_title(by_rel[key]), dir_page_id(key)))
    return " · ".join(parts)

def build_dir_page(directory: Item, source_root: Path, items, markdown_map,
                   owner, repo, branch) -> str:
    title = section_title(directory)
    lines = [breadcrumbs(directory.rel, items, dir_page_id(directory.rel)), "", f"# {title}", ""]
    name = Path(directory.rel).name
    if name in SUBJECTS:
        lines += [SUBJECTS[name][1], ""]
    elif name in DOCUMENTS:
        lines += [DOCUMENTS[name][1], ""]
    # Navigation pages have a purpose-built layout; old folder README catalogs
    # are not embedded again, avoiding duplicate lists and directory trees.
    kids = children(items, directory.rel)
    subdirs = [x for x in kids if x.kind == "dir"]
    direct = [x for x in kids if x.kind != "dir"]
    if name in SUBJECTS:
        lines += ["Выберите курс и откройте нужный вид материалов.", "",
                  "| Курс | Лекции | Практические работы |", "| :--- | :---: | :---: |"]
        for course in subdirs:
            sections = {Path(x.rel).name: x for x in children(items, course.rel) if x.kind == "dir"}
            cells = [md_link("Открыть", dir_page_id(sections[key].rel)) if key in sections else "—"
                     for key in ("Лекции", "Практические задания")]
            lines.append(f"| {md_link(Path(course.rel).name, dir_page_id(course.rel))} | {cells[0]} | {cells[1]} |")
        lines.append("")
    elif name in ("Лекции", "Практические задания"):
        lines += ["Откройте материал из списка. Содержание доступно прямо в Wiki.", ""]
        lines += material_table(descendants(items, directory.rel), markdown_map, owner, repo, branch)
    else:
        for subdir in subdirs:
            lines += [f"## {md_link(section_title(subdir), dir_page_id(subdir.rel))}", ""]
            lines += material_table(descendants(items, subdir.rel), markdown_map, owner, repo, branch)
    if direct and name not in ("Лекции", "Практические задания"):
        if subdirs:
            lines += ["## Материалы раздела", ""]
        lines += material_table(direct, markdown_map, owner, repo, branch)
    if not kids:
        lines += ["_Материалы пока не опубликованы._", ""]
    lines += ["---", "", f"[Открыть папку на GitHub]({repo_tree_url(owner, repo, branch, directory.rel)})", ""]
    return "\n".join(lines)

def build_markdown_page(item: Item, markdown_map, owner, repo, branch, items=None) -> str:
    items = items or []
    text = read_markdown(item.abs_path) or ""
    text = rewrite_markdown(text, item.rel, markdown_map, owner, repo, branch)
    lines = [breadcrumbs(item.rel, items, markdown_map[item.rel]), "", "---", "", text.strip(), "", "---", ""]
    # Sequential reading within the same lecture/practical section.
    parts = PurePosixPath(item.rel).parts
    section_rel = next(("/".join(parts[:i + 1]) for i, part in enumerate(parts[:-1])
                        if part in ("Лекции", "Практические задания")), item.parent_rel)
    peers = [x for x in items if x.kind == "markdown" and
             (x.rel.startswith(section_rel + "/") if section_rel else x.parent_rel == "")]
    navigation = []
    if item in peers:
        index = peers.index(item)
        if index:
            navigation.append(md_link("← " + material_title(peers[index - 1]), markdown_map[peers[index - 1].rel]))
        if index + 1 < len(peers):
            navigation.append(md_link(material_title(peers[index + 1]) + " →", markdown_map[peers[index + 1].rel]))
    if navigation:
        lines += [" · ".join(navigation), ""]
    lines += [f"[Оригинал материала на GitHub]({repo_blob_url(owner, repo, branch, item.rel)})", ""]
    return "\n".join(lines)

def build_home(items, owner, repo, branch) -> str:
    roots = {Path(x.rel).name: x for x in top_level_dirs(items)}
    lines = ["# 🎓 Таврический колледж", "",
             "**Учебные материалы по микропроцессорным системам и программированию микроконтроллеров**", "",
             "Специальность **09.02.01 «Компьютерные системы и комплексы»** · **3 и 4 курс**", "",
             "Лекции, практические работы и материалы для аттестации — с удобной навигацией и чтением прямо в Wiki.", "",
             "## 📚 Выберите дисциплину и курс", "",
             "| Дисциплина | Курс | Лекции | Практические работы |", "| :--- | :---: | :---: | :---: |"]
    for name, (title, _) in SUBJECTS.items():
        if name not in roots:
            continue
        for course in children(items, roots[name].rel):
            if course.kind != "dir":
                continue
            sections = {Path(x.rel).name: x for x in children(items, course.rel) if x.kind == "dir"}
            cells = [md_link("Открыть", dir_page_id(sections[key].rel)) if key in sections else "—"
                     for key in ("Лекции", "Практические задания")]
            lines.append(f"| {md_link(title, dir_page_id(roots[name].rel))} | {md_link(Path(course.rel).name, dir_page_id(course.rel))} | {cells[0]} | {cells[1]} |")
    lines.append("")
    for name, (title, description) in SUBJECTS.items():
        if name in roots:
            lines += [f"**{title}.** {description}", ""]
    lines += ["## 📋 Документы и аттестация", "", "| Раздел | Что внутри |", "| :--- | :--- |"]
    for name, root in roots.items():
        if name in SUBJECTS:
            continue
        description = DOCUMENTS.get(name, ("", "Образец задания, КИМ и приложения." if name.startswith("Демоэкзамен") else "Дополнительные материалы."))[1]
        lines.append(f"| {md_link(section_title(root), dir_page_id(root.rel))} | {description} |")
    lines += ["", "## 🧭 С чего начать", "",
              "1. Выберите дисциплину, курс и нужный вид материалов в таблице выше.",
              "2. Откройте лекцию или практическую работу. Для задания прочитайте условия, правило выбора варианта и требования к отчёту.",
              "3. Переходите между материалами по ссылкам внизу страницы или используйте боковое меню.", ""]
    root_files = top_level_files(items)
    if root_files:
        lines += ["## Дополнительные материалы", ""]
        lines += material_table(root_files, {x.rel: markdown_page_id(x.rel) for x in root_files}, owner, repo, branch)
    lines += ["---", "", f"[Открыть основной репозиторий](https://github.com/{owner}/{repo})", "",
              "Материалы Wiki автоматически обновляются при изменении основного репозитория.", ""]
    return "\n".join(lines)

def build_sidebar(items, owner, repo) -> str:
    roots = {Path(x.rel).name: x for x in top_level_dirs(items)}
    lines = ["**[🎓 Главная](Home)**", ""]
    for name, (title, _) in SUBJECTS.items():
        if name not in roots:
            continue
        lines += ["---", "", "**" + md_link(title, dir_page_id(roots[name].rel)) + "**", ""]
        for course in children(items, roots[name].rel):
            if course.kind != "dir":
                continue
            links = []
            for section in children(items, course.rel):
                if section.kind == "dir":
                    label = "Практика" if Path(section.rel).name == "Практические задания" else Path(section.rel).name
                    links.append(md_link(label, dir_page_id(section.rel)))
            lines += ["**" + md_link(Path(course.rel).name, dir_page_id(course.rel)) + "**", "",
                      " · ".join(links), ""]
    lines += ["---", "", "**Документы и аттестация**", ""]
    for name, root in roots.items():
        if name not in SUBJECTS:
            lines.append("- " + md_link(section_title(root), dir_page_id(root.rel)))
    lines += ["", "---", "", f"[Репозиторий ↗](https://github.com/{owner}/{repo})", ""]
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
    if source == wiki_dir or source.is_relative_to(wiki_dir):
        raise ValueError("Wiki output must not contain the source repository")
    items = [x for x in discover(source) if not x.abs_path.is_relative_to(wiki_dir)]
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
        "Таврический колледж",
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
                item, markdown_map, args.owner, args.repo, args.branch, items
            ),
        )

    print(f"Wiki каталогов: {len([x for x in items if x.kind == 'dir'])}")
    print(f"Markdown-страниц: {len(markdowns)}")
    print(f"Файлов-ссылок: {len([x for x in items if x.kind == 'file'])}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
