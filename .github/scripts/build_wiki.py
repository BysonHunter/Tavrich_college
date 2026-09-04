#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

ROOTS = ("МПС", "ПМК", "РПД", "ФОС", "АккМон")
SUBJECTS = ("МПС", "ПМК")

# Человекочитаемые названия документов, у которых первый H1 внутри файла
# является не названием документа, а названием первого раздела.
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

    "АккМон/Вопросы_к_аккредитации_Микропроцессорные_системы.md":
        "Вопросы к аккредитации — микропроцессорные системы",
    "АккМон/Вопросы_к_аккредитации_Программирование_микроконтроллеров_11-09-2026.md":
        "Вопросы к аккредитации — программирование микроконтроллеров",
    "АккМон/ФОС_Микропроцессорные_системы_09.02.01.md":
        "ФОС — микропроцессорные системы, 3 курс",
    "АккМон/ФОС_Микропроцессорные_системы_4_курс_09.02.01.md":
        "ФОС — микропроцессорные системы, 4 курс",
    "АккМон/ФОС_Программирование_микроконтроллеров_09.02.01.md":
        "ФОС — программирование микроконтроллеров, 3 курс",
    "АккМон/ФОС_Программирование_микроконтроллеров_4_курс_09.02.01.md":
        "ФОС — программирование микроконтроллеров, 4 курс",
}


@dataclass
class Page:
    source_path: str
    page_file: str
    page_id: str
    title: str
    root: str
    course: str | None
    category: str | None


def natural_key(text: str):
    return [int(x) if x.isdigit() else x.casefold()
            for x in re.split(r"(\d+)", text)]


def sanitize(text: str) -> str:
    text = text.strip().replace("_", "-").replace(" ", "-")
    text = re.sub(r'[\\/:*?"<>|#]+', "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-.")


def enc(path: str) -> str:
    return "/".join(quote(p, safe="-_.~") for p in PurePosixPath(path).parts)


def raw_url(owner: str, repo: str, branch: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{enc(path)}"


def blob_url(owner: str, repo: str, branch: str, path: str) -> str:
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{enc(path)}"


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            value = re.sub(r"[*_`]+", "", m.group(1)).strip()
            if value:
                return value
    return fallback


def detect_course_and_index(parts: tuple[str, ...]) -> tuple[str | None, int | None]:
    for idx, part in enumerate(parts):
        m = re.fullmatch(r"(\d+)\s*курс", part, re.I)
        if m:
            return f"{int(m.group(1))} курс", idx
    return None, None


def detect_category(parts: tuple[str, ...], course_idx: int | None) -> str | None:
    if course_idx is None:
        return None
    # category exists only when there is a directory between course and file
    if course_idx + 1 >= len(parts) - 1:
        return "Материалы"
    return parts[course_idx + 1]


def make_page_file(rel: str, used: set[str]) -> str:
    p = PurePosixPath(rel)
    parts = p.parts
    root = parts[0]
    course, course_idx = detect_course_and_index(parts)
    category = detect_category(parts, course_idx)

    bits = [sanitize(root)]
    if course:
        bits.append(course.split()[0])
    if category and category not in ("Лекции", "Материалы"):
        bits.append(sanitize(category))
    bits.append(sanitize(p.stem))

    base = "-".join(x for x in bits if x)
    candidate = base + ".md"
    n = 2
    while candidate in used:
        candidate = f"{base}-{n}.md"
        n += 1
    used.add(candidate)
    return candidate


def discover(source: Path) -> list[Page]:
    records = []

    for root in ROOTS:
        folder = source / root
        if not folder.exists():
            continue

        for p in folder.rglob("*.md"):
            # README каталогов используется в основном репозитории,
            # но не дублируется как отдельная Wiki-страница.
            if p.name.casefold() == "readme.md":
                continue

            rel = p.relative_to(source).as_posix()
            text = p.read_text(encoding="utf-8")
            parts = PurePosixPath(rel).parts
            course, course_idx = detect_course_and_index(parts)
            category = detect_category(parts, course_idx) if root in SUBJECTS else None
            title = TITLE_OVERRIDES.get(rel, extract_title(text, p.stem))
            records.append((rel, title, root, course, category))

    used: set[str] = set()
    pages: list[Page] = []

    for rel, title, root, course, category in sorted(
        records, key=lambda r: natural_key(r[0])
    ):
        pf = make_page_file(rel, used)
        pages.append(
            Page(
                source_path=rel,
                page_file=pf,
                page_id=Path(pf).stem,
                title=title,
                root=root,
                course=course,
                category=category,
            )
        )

    return pages


def resolve_relative(source_path: str, target: str) -> str | None:
    target = target.strip()

    if not target or target.startswith(
        ("#", "http://", "https://", "mailto:", "data:", "//")
    ):
        return None

    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]

    target = unquote(target.split("#", 1)[0])
    base = PurePosixPath(source_path).parent
    return os.path.normpath((base / target).as_posix()).replace("\\", "/")


def rewrite(
    text: str,
    page: Page,
    by_source: dict[str, Page],
    owner: str,
    repo: str,
    branch: str,
) -> str:
    # Markdown images
    img_re = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def img_sub(m):
        resolved = resolve_relative(page.source_path, m.group(2))
        if resolved is None:
            return m.group(0)
        return f"![{m.group(1)}]({raw_url(owner, repo, branch, resolved)})"

    text = img_re.sub(img_sub, text)

    # HTML images
    html_img_re = re.compile(
        r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])',
        re.I,
    )

    def html_sub(m):
        resolved = resolve_relative(page.source_path, m.group(2))
        if resolved is None:
            return m.group(0)
        return m.group(1) + raw_url(owner, repo, branch, resolved) + m.group(3)

    text = html_img_re.sub(html_sub, text)

    # Relative Markdown links between source documents
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

        resolved = resolve_relative(page.source_path, target_path)
        if resolved is None:
            return m.group(0)

        other = by_source.get(resolved)
        if other:
            return md_link(label, other.page_id + anchor)

        return f"[{label}]({blob_url(owner, repo, branch, resolved)}{anchor})"

    return link_re.sub(link_sub, text)


def write(path: Path, text: str):
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def md_link(label: str, page_id: str) -> str:
    """
    Standard Markdown link for GitHub Wiki.

    Do NOT use [[label|page]] inside Markdown tables:
    the pipe character is parsed as a table-cell separator by GitHub.
    """
    return f"[{label}]({page_id})"


def table_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
    )


def clean_wiki(wiki_dir: Path):
    wiki_dir.mkdir(parents=True, exist_ok=True)

    for item in wiki_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def pages_for(
    pages: list[Page],
    root=None,
    course=None,
    category=None,
) -> list[Page]:
    out = pages

    if root is not None:
        out = [p for p in out if p.root == root]
    if course is not None:
        out = [p for p in out if p.course == course]
    if category is not None:
        out = [p for p in out if p.category == category]

    return out


def category_id(root: str, course: str, category: str) -> str:
    return f"{root}-{course.split()[0]}-{sanitize(category)}"


def category_sort(category: str):
    if category == "Лекции":
        return (0, natural_key(category))
    if "Практи" in category:
        return (1, natural_key(category))
    return (2, natural_key(category))


def build_home(wiki_dir: Path):
    write(
        wiki_dir / "Home.md",
        """# Учебно-методические материалы Таврического колледжа

Материалы для специальности **09.02.01 «Компьютерные системы и комплексы»**.

## Дисциплины

- [МДК.02.01 «Микропроцессорные системы»](МПС)
- [МДК.02.02 «Программирование микроконтроллеров»](ПМК)

## Документация

- [Рабочие программы](РПД)
- [Оценочные материалы](ФОС)
- [Аккредитационный мониторинг](АккМон)

> Wiki формируется автоматически из основной ветки `main`.
""",
    )


def build_subject(
    wiki_dir: Path,
    pages: list[Page],
    root: str,
    full_name: str,
):
    subject_pages = pages_for(pages, root=root)
    courses = sorted(
        {p.course for p in subject_pages if p.course},
        key=natural_key,
    )

    lines = [f"# {full_name}", "", "## Курсы", ""]

    for course in courses:
        course_page_id = f"{root}-{course.split()[0]}-курс"
        lines.append(f"- {md_link(course, course_page_id)}")

    lines += ["", "[🏠 На главную](Home)"]
    write(wiki_dir / f"{root}.md", "\n".join(lines))

    for course in courses:
        course_pages = pages_for(pages, root=root, course=course)
        categories = sorted(
            {p.category or "Материалы" for p in course_pages},
            key=category_sort,
        )

        course_page_id = f"{root}-{course.split()[0]}-курс"
        course_lines = [f"# {full_name} — {course}", ""]

        for category in categories:
            items = pages_for(
                pages,
                root=root,
                course=course,
                category=category,
            )
            if not items:
                continue

            cid = category_id(root, course, category)

            course_lines += [
                f"## {category}",
                "",
                md_link("Открыть раздел", cid),
                "",
            ]

            for p in items:
                course_lines.append(f"- {md_link(p.title, p.page_id)}")

            course_lines.append("")

            cat_lines = [
                f"# {full_name} — {course}",
                "",
                f"## {category}",
                "",
            ]

            for i, p in enumerate(items, 1):
                cat_lines.append(f"{i}. {md_link(p.title, p.page_id)}")

            cat_lines += [
                "",
                f"{md_link('← ' + course, course_page_id)} · "
                f"{md_link('← ' + root, root)} · "
                f"[🏠 Главная](Home)",
            ]

            write(wiki_dir / f"{cid}.md", "\n".join(cat_lines))

        course_lines += [
            f"{md_link('← ' + root, root)} · [🏠 Главная](Home)"
        ]

        write(
            wiki_dir / f"{course_page_id}.md",
            "\n".join(course_lines),
        )


def build_docs(
    wiki_dir: Path,
    pages: list[Page],
    root: str,
    title: str,
):
    lines = [
        f"# {title}",
        "",
        "| Материал | Исходный файл |",
        "|---|---|",
    ]

    for p in pages_for(pages, root=root):
        # ВАЖНО: внутри таблицы используются обычные Markdown-ссылки.
        # [[label|page]] здесь нельзя использовать, т.к. | разбивает строку таблицы.
        label = table_escape(p.title)
        source = table_escape(p.source_path)
        lines.append(
            f"| {md_link(label, p.page_id)} | `{source}` |"
        )

    lines += ["", "[🏠 На главную](Home)"]
    write(wiki_dir / f"{root}.md", "\n".join(lines))


def build_sidebar(wiki_dir: Path, pages: list[Page]):
    lines = [
        "## 🏠 Главная",
        "[Главная](Home)",
        "",
        "---",
        "",
    ]

    for root, label in (
        ("МПС", "🖥 МПС"),
        ("ПМК", "🔧 ПМК"),
    ):
        lines += [
            f"## {label}",
            md_link(f"Обзор {root}", root),
            "",
        ]

        courses = sorted(
            {p.course for p in pages if p.root == root and p.course},
            key=natural_key,
        )

        for course in courses:
            course_page_id = f"{root}-{course.split()[0]}-курс"
            lines += [
                f"**{md_link(course, course_page_id)}**",
                "",
            ]

            cats = sorted(
                {
                    p.category or "Материалы"
                    for p in pages_for(
                        pages,
                        root=root,
                        course=course,
                    )
                },
                key=category_sort,
            )

            for cat in cats:
                lines.append(
                    f"- {md_link(cat, category_id(root, course, cat))}"
                )

            lines.append("")

        lines += ["---", ""]

    lines += [
        "## 📚 Документация",
        f"- {md_link('Рабочие программы', 'РПД')}",
        f"- {md_link('Оценочные материалы', 'ФОС')}",
        f"- {md_link('Аккредитационный мониторинг', 'АккМон')}",
    ]

    write(wiki_dir / "_Sidebar.md", "\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--owner", default="BysonHunter")
    ap.add_argument("--repo", default="Tavrich_college")
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    wiki_dir = Path(args.wiki).resolve()

    pages = discover(source)
    by_source = {p.source_path: p for p in pages}

    clean_wiki(wiki_dir)

    for page in pages:
        src = source / page.source_path
        text = rewrite(
            src.read_text(encoding="utf-8"),
            page,
            by_source,
            args.owner,
            args.repo,
            args.branch,
        )

        if (
            page.root in SUBJECTS
            and page.course
            and page.category
        ):
            parent = category_id(
                page.root,
                page.course,
                page.category,
            )
        else:
            parent = page.root

        header = (
            f"[🏠 Главная](Home) · "
            f"{md_link('← К разделу', parent)}\n\n"
            f"> **Источник:** "
            f"[{page.source_path}]"
            f"({blob_url(args.owner, args.repo, args.branch, page.source_path)})  \n"
            f"> Страница автоматически синхронизируется "
            f"с веткой `{args.branch}`.\n\n"
            "---\n\n"
        )

        write(
            wiki_dir / page.page_file,
            header + text.lstrip(),
        )

    build_home(wiki_dir)

    build_subject(
        wiki_dir,
        pages,
        "МПС",
        "МДК.02.01 «Микропроцессорные системы»",
    )
    build_subject(
        wiki_dir,
        pages,
        "ПМК",
        "МДК.02.02 «Программирование микроконтроллеров»",
    )

    build_docs(
        wiki_dir,
        pages,
        "РПД",
        "Рабочие программы дисциплин",
    )
    build_docs(
        wiki_dir,
        pages,
        "ФОС",
        "Оценочные материалы",
    )
    build_docs(
        wiki_dir,
        pages,
        "АккМон",
        "Аккредитационный мониторинг",
    )

    build_sidebar(wiki_dir, pages)

    write(
        wiki_dir / "_Footer.md",
        "---\n"
        "**09.02.01 «Компьютерные системы и комплексы»** · "
        "[Основной репозиторий]"
        "(https://github.com/BysonHunter/Tavrich_college)",
    )

    print(f"Сгенерировано страниц материалов: {len(pages)}")
    for root in ROOTS:
        print(f"{root}: {len([p for p in pages if p.root == root])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
