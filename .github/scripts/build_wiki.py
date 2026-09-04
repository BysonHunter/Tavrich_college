#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Генератор GitHub Wiki для репозитория BysonHunter/Tavrich_college.

Что делает:
1. Берёт Markdown-файлы из локального клона Tavrich_college.
2. Создаёт понятные Wiki-страницы с устойчивыми именами.
3. Переписывает относительные ссылки на изображения так, чтобы изображения
   загружались из основного репозитория и не дублировались в Wiki.
4. Создаёт Home.md, _Sidebar.md, _Footer.md и страницы-разделы.
5. Копирует РПД, ФОС, материалы АккМон и все текущие лекции МПС/ПМК.
6. Автоматически подхватывает новые Markdown-файлы, которые позже появятся
   в основных учебных папках.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

DEFAULT_OWNER = "BysonHunter"
DEFAULT_REPO = "Tavrich_college"
DEFAULT_BRANCH = "main"

# Точное отображение текущих файлов репозитория на удобные Wiki-страницы.
PAGE_MAP = {
    # Аккредитационный мониторинг
    "АккМон/Вопросы_к_аккредитации_Микропроцессорные_системы.md":
        "АккМон-Вопросы-МПС.md",
    "АккМон/Вопросы_к_аккредитации_Программирование_микроконтроллеров_11-09-2026.md":
        "АккМон-Вопросы-ПМК.md",
    "АккМон/ФОС_Микропроцессорные_системы_09.02.01.md":
        "АккМон-ФОС-МПС-3-курс.md",
    "АккМон/ФОС_Микропроцессорные_системы_4_курс_09.02.01.md":
        "АккМон-ФОС-МПС-4-курс.md",
    "АккМон/ФОС_Программирование_микроконтроллеров_09.02.01.md":
        "АккМон-ФОС-ПМК-3-курс.md",
    "АккМон/ФОС_Программирование_микроконтроллеров_4_курс_09.02.01.md":
        "АккМон-ФОС-ПМК-4-курс.md",

    # РПД
    "РПД/РП_МДК0201_МПС_КСК_2025.md":
        "РПД-МПС-3-курс.md",
    "РПД/РП_МДК0201_Микропроцессорные_системы_4_курс_КСК_2025.md":
        "РПД-МПС-4-курс.md",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_КСК_2025.md":
        "РПД-ПМК-3-курс.md",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_4_курс_КСК_2025.md":
        "РПД-ПМК-4-курс.md",

    # Входной контроль
    "ФОС/Входной_контроль_МПС_и_программирование_МК_3_курс.md":
        "ФОС-Входной-контроль-3-курс.md",

    # МПС
    "МПС/3 курс/Лекция_1_Общие_понятия_МПС/Лекция_1_Общие_понятия_МПС.md":
        "МПС-3-Лекция-1-Общие-понятия.md",
    "МПС/3 курс/Лекция_2_Микропроцессор/МП_Лекция_2_Микропроцессор.md":
        "МПС-3-Лекция-2-Микропроцессор.md",
    "МПС/4 курс/Лекции/lecture_01_mps/lecture_01_etapy_proektirovaniya_mps.md":
        "МПС-4-Лекция-1-Этапы-проектирования.md",

    # ПМК
    "ПМК/3 курс/Лекция_1_Основы_архитектуры_микроконтроллеров/Лекция_1_Основы_архитектуры_микроконтроллеров.md":
        "ПМК-3-Лекция-1-Архитектура-микроконтроллеров.md",
    "ПМК/3 курс/Лекция_2_ARM_Cortex_M/Лекция_2_ARM_Cortex_M_с_инфографикой.md":
        "ПМК-3-Лекция-2-ARM-Cortex-M.md",
    "ПМК/3 курс/Лекция_3_Основы_программирования_Arduino/Лекция_3_Основы_программирования_Arduino.md":
        "ПМК-3-Лекция-3-Основы-Arduino.md",
    "ПМК/4 курс/Лекции/Лекция_5_1_AVR_CortexM_STM32_ESP32_MD/Лекция_5_1_AVR_ARM_Cortex-M_STM32_ESP32.md":
        "ПМК-4-Лекция-5-1-AVR-CortexM-STM32-ESP32.md",
}

PARENT_MAP = {
    # АккМон
    "АккМон/Вопросы_к_аккредитации_Микропроцессорные_системы.md": "АккМон",
    "АккМон/Вопросы_к_аккредитации_Программирование_микроконтроллеров_11-09-2026.md": "АккМон",
    "АккМон/ФОС_Микропроцессорные_системы_09.02.01.md": "АккМон",
    "АккМон/ФОС_Микропроцессорные_системы_4_курс_09.02.01.md": "АккМон",
    "АккМон/ФОС_Программирование_микроконтроллеров_09.02.01.md": "АккМон",
    "АккМон/ФОС_Программирование_микроконтроллеров_4_курс_09.02.01.md": "АккМон",

    # РПД / ФОС
    "РПД/РП_МДК0201_МПС_КСК_2025.md": "РПД",
    "РПД/РП_МДК0201_Микропроцессорные_системы_4_курс_КСК_2025.md": "РПД",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_КСК_2025.md": "РПД",
    "РПД/РП_МДК0202_Программирование_микроконтроллеров_4_курс_КСК_2025.md": "РПД",
    "ФОС/Входной_контроль_МПС_и_программирование_МК_3_курс.md": "ФОС",

    # МПС
    "МПС/3 курс/Лекция_1_Общие_понятия_МПС/Лекция_1_Общие_понятия_МПС.md": "МПС-3-курс",
    "МПС/3 курс/Лекция_2_Микропроцессор/МП_Лекция_2_Микропроцессор.md": "МПС-3-курс",
    "МПС/4 курс/Лекции/lecture_01_mps/lecture_01_etapy_proektirovaniya_mps.md": "МПС-4-курс",

    # ПМК
    "ПМК/3 курс/Лекция_1_Основы_архитектуры_микроконтроллеров/Лекция_1_Основы_архитектуры_микроконтроллеров.md": "ПМК-3-курс",
    "ПМК/3 курс/Лекция_2_ARM_Cortex_M/Лекция_2_ARM_Cortex_M_с_инфографикой.md": "ПМК-3-курс",
    "ПМК/3 курс/Лекция_3_Основы_программирования_Arduino/Лекция_3_Основы_программирования_Arduino.md": "ПМК-3-курс",
    "ПМК/4 курс/Лекции/Лекция_5_1_AVR_CortexM_STM32_ESP32_MD/Лекция_5_1_AVR_ARM_Cortex-M_STM32_ESP32.md": "ПМК-4-курс",
}

DISPLAY_NAMES = {
    "АккМон-Вопросы-МПС": "Вопросы к аккредитации — МПС",
    "АккМон-Вопросы-ПМК": "Вопросы к аккредитации — ПМК",
    "АккМон-ФОС-МПС-3-курс": "ФОС МПС — 3 курс",
    "АккМон-ФОС-МПС-4-курс": "ФОС МПС — 4 курс",
    "АккМон-ФОС-ПМК-3-курс": "ФОС ПМК — 3 курс",
    "АккМон-ФОС-ПМК-4-курс": "ФОС ПМК — 4 курс",
    "РПД-МПС-3-курс": "Рабочая программа МПС — 3 курс",
    "РПД-МПС-4-курс": "Рабочая программа МПС — 4 курс",
    "РПД-ПМК-3-курс": "Рабочая программа ПМК — 3 курс",
    "РПД-ПМК-4-курс": "Рабочая программа ПМК — 4 курс",
    "ФОС-Входной-контроль-3-курс": "Входной контроль — 3 курс",
    "МПС-3-Лекция-1-Общие-понятия": "Лекция 1. Общие понятия МПС",
    "МПС-3-Лекция-2-Микропроцессор": "Лекция 2. Микропроцессор",
    "МПС-4-Лекция-1-Этапы-проектирования": "Лекция 1. Этапы проектирования МПС",
    "ПМК-3-Лекция-1-Архитектура-микроконтроллеров": "Лекция 1. Основы архитектуры микроконтроллеров",
    "ПМК-3-Лекция-2-ARM-Cortex-M": "Лекция 2. ARM Cortex-M",
    "ПМК-3-Лекция-3-Основы-Arduino": "Лекция 3. Основы программирования Arduino",
    "ПМК-4-Лекция-5-1-AVR-CortexM-STM32-ESP32": "Лекция 5.1. AVR, Cortex-M, STM32 и ESP32",
}


def wiki_link(label: str, page: str) -> str:
    return f"[[{label}|{page}]]"


def posix(path: Path) -> str:
    return path.as_posix()


def encode_repo_path(path: str) -> str:
    """URL-encode each component while preserving /."""
    return "/".join(quote(part, safe="-_.~") for part in PurePosixPath(path).parts)


def source_blob_url(owner: str, repo: str, branch: str, source_path: str) -> str:
    return f"https://github.com/{owner}/{repo}/blob/{branch}/{encode_repo_path(source_path)}"


def source_raw_url(owner: str, repo: str, branch: str, source_path: str) -> str:
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encode_repo_path(source_path)}"


def sanitize_page_component(text: str) -> str:
    text = text.strip().replace("_", "-").replace(" ", "-")
    text = re.sub(r'[\\/:*?"<>|#]+', "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-.")


def fallback_page_name(source_path: str) -> str:
    p = PurePosixPath(source_path)
    stem = p.stem
    parts = [sanitize_page_component(x) for x in p.parts[:-1]]
    parts.append(sanitize_page_component(stem))
    return "-".join(x for x in parts if x) + ".md"


def resolve_relative(source_path: str, target: str) -> str | None:
    target = target.strip()
    if not target or target.startswith(("#", "http://", "https://", "mailto:", "data:", "//")):
        return None

    # Markdown permits <path with spaces>.
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]

    # Preserve optional anchor but resolve only the path part.
    target_path = target.split("#", 1)[0]
    target_path = unquote(target_path)

    base = PurePosixPath(source_path).parent
    norm = os.path.normpath((base / target_path).as_posix()).replace("\\", "/")
    return norm


def rewrite_markdown(content: str, source_path: str, page_map: dict[str, str],
                     owner: str, repo: str, branch: str) -> str:
    # 1) Markdown images.
    image_re = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

    def image_sub(m: re.Match) -> str:
        alt, target = m.group(1), m.group(2).strip()

        # Split optional quoted title very conservatively.
        path_target = target
        title_suffix = ""
        mt = re.match(r'^(<[^>]+>|[^\s]+)(\s+["\'][^"\']*["\'])$', target)
        if mt:
            path_target, title_suffix = mt.group(1), mt.group(2)

        resolved = resolve_relative(source_path, path_target)
        if resolved is None:
            return m.group(0)

        raw = source_raw_url(owner, repo, branch, resolved)
        return f"![{alt}]({raw}{title_suffix})"

    content = image_re.sub(image_sub, content)

    # 2) HTML <img src="...">.
    html_img_re = re.compile(r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'])', re.I)

    def html_img_sub(m: re.Match) -> str:
        resolved = resolve_relative(source_path, m.group(2))
        if resolved is None:
            return m.group(0)
        return m.group(1) + source_raw_url(owner, repo, branch, resolved) + m.group(3)

    content = html_img_re.sub(html_img_sub, content)

    # 3) Ordinary Markdown links to other source .md files.
    link_re = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')

    def link_sub(m: re.Match) -> str:
        label, target = m.group(1), m.group(2).strip()
        if target.startswith(("#", "http://", "https://", "mailto:", "//")):
            return m.group(0)

        # Separate #anchor.
        if "#" in target:
            target_path, anchor = target.split("#", 1)
            anchor = "#" + anchor
        else:
            target_path, anchor = target, ""

        resolved = resolve_relative(source_path, target_path)
        if resolved is None:
            return m.group(0)

        if resolved in page_map:
            page = Path(page_map[resolved]).stem
            return f"[{label}]({page}{anchor})"

        # For other relative resources, point back to the main repository.
        return f"[{label}]({source_blob_url(owner, repo, branch, resolved)}{anchor})"

    content = link_re.sub(link_sub, content)
    return content


def page_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        m = re.match(r'^\s*#\s+(.+?)\s*$', line)
        if m:
            return re.sub(r'[*_`]+', '', m.group(1)).strip()
    return fallback


def add_wiki_header(content: str, source_path: str, parent_page: str,
                    owner: str, repo: str, branch: str) -> str:
    src_url = source_blob_url(owner, repo, branch, source_path)
    header = (
        f"[🏠 Главная](Home) · [← К разделу]({parent_page})\n\n"
        f"> **Источник:** [{source_path}]({src_url})  \n"
        f"> Эта Wiki-страница синхронизирована с основным репозиторием. "
        f"Изображения загружаются из основного репозитория и не дублируются в Wiki.\n\n"
        "---\n\n"
    )
    return header + content.lstrip()


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def section_page(title: str, intro: str, rows: list[tuple[str, str, str]]) -> str:
    lines = [f"# {title}", "", intro, "", "| Раздел | Материал | Описание |",
             "|---|---|---|"]
    for group, page, descr in rows:
        label = DISPLAY_NAMES.get(page, page)
        lines.append(f"| {group} | {wiki_link(label, page)} | {descr} |")
    lines += ["", "[🏠 На главную](Home)"]
    return "\n".join(lines)


def build_navigation_pages(wiki_dir: Path) -> None:
    home = """# Учебно-методические материалы Таврического колледжа

Материалы для студентов специальности **09.02.01 «Компьютерные системы и комплексы»**.

В Wiki представлены два междисциплинарных курса:

| МДК | Курс | Навигация |
|---|---|---|
| **МДК.02.01 «Микропроцессорные системы»** | 3 и 4 курс | [[Перейти к МПС|МПС]] |
| **МДК.02.02 «Программирование микроконтроллеров»** | 3 и 4 курс | [[Перейти к ПМК|ПМК]] |

## Учебно-методическая документация

- [[Рабочие программы дисциплин|РПД]]
- [[Оценочные материалы и входной контроль|ФОС]]
- [[Материалы аккредитационного мониторинга|АккМон]]

## Быстрый переход по курсам

### Микропроцессорные системы

- [[МПС — 3 курс|МПС-3-курс]]
- [[МПС — 4 курс|МПС-4-курс]]

### Программирование микроконтроллеров

- [[ПМК — 3 курс|ПМК-3-курс]]
- [[ПМК — 4 курс|ПМК-4-курс]]

---

**Основной репозиторий:** [BysonHunter/Tavrich_college](https://github.com/BysonHunter/Tavrich_college)
"""
    write_text(wiki_dir / "Home.md", home)

    mps = """# МДК.02.01 «Микропроцессорные системы»

Учебные материалы по микропроцессорным системам для студентов специальности
**09.02.01 «Компьютерные системы и комплексы»**.

## Курсы

- [[3 курс|МПС-3-курс]]
- [[4 курс|МПС-4-курс]]

## Связанные документы

- [[Рабочие программы|РПД]]
- [[ФОС и аккредитационные материалы|АккМон]]
- [[Входной контроль|ФОС]]

[🏠 На главную](Home)
"""
    write_text(wiki_dir / "МПС.md", mps)

    mps3 = """# Микропроцессорные системы — 3 курс

## Лекции

1. [[Лекция 1. Общие понятия МПС|МПС-3-Лекция-1-Общие-понятия]]
2. [[Лекция 2. Микропроцессор|МПС-3-Лекция-2-Микропроцессор]]

## Документация

- [[Рабочая программа МПС — 3 курс|РПД-МПС-3-курс]]
- [[ФОС МПС — 3 курс|АккМон-ФОС-МПС-3-курс]]
- [[Вопросы к аккредитации — МПС|АккМон-Вопросы-МПС]]
- [[Входной контроль — 3 курс|ФОС-Входной-контроль-3-курс]]

[[← МПС|МПС]] · [🏠 Главная](Home)
"""
    write_text(wiki_dir / "МПС-3-курс.md", mps3)

    mps4 = """# Микропроцессорные системы — 4 курс

## Лекции

1. [[Лекция 1. Этапы проектирования МПС|МПС-4-Лекция-1-Этапы-проектирования]]

## Документация

- [[Рабочая программа МПС — 4 курс|РПД-МПС-4-курс]]
- [[ФОС МПС — 4 курс|АккМон-ФОС-МПС-4-курс]]

[[← МПС|МПС]] · [🏠 Главная](Home)
"""
    write_text(wiki_dir / "МПС-4-курс.md", mps4)

    pmk = """# МДК.02.02 «Программирование микроконтроллеров»

Учебные материалы по программированию микроконтроллеров для студентов специальности
**09.02.01 «Компьютерные системы и комплексы»**.

## Курсы

- [[3 курс|ПМК-3-курс]]
- [[4 курс|ПМК-4-курс]]

## Связанные документы

- [[Рабочие программы|РПД]]
- [[ФОС и аккредитационные материалы|АккМон]]
- [[Входной контроль|ФОС]]

[🏠 На главную](Home)
"""
    write_text(wiki_dir / "ПМК.md", pmk)

    pmk3 = """# Программирование микроконтроллеров — 3 курс

## Лекции

1. [[Лекция 1. Основы архитектуры микроконтроллеров|ПМК-3-Лекция-1-Архитектура-микроконтроллеров]]
2. [[Лекция 2. ARM Cortex-M|ПМК-3-Лекция-2-ARM-Cortex-M]]
3. [[Лекция 3. Основы программирования Arduino|ПМК-3-Лекция-3-Основы-Arduino]]

## Документация

- [[Рабочая программа ПМК — 3 курс|РПД-ПМК-3-курс]]
- [[ФОС ПМК — 3 курс|АккМон-ФОС-ПМК-3-курс]]
- [[Вопросы к аккредитации — ПМК|АккМон-Вопросы-ПМК]]
- [[Входной контроль — 3 курс|ФОС-Входной-контроль-3-курс]]

[[← ПМК|ПМК]] · [🏠 Главная](Home)
"""
    write_text(wiki_dir / "ПМК-3-курс.md", pmk3)

    pmk4 = """# Программирование микроконтроллеров — 4 курс

## Лекции

1. [[Лекция 5.1. AVR, ARM Cortex-M, STM32 и ESP32|ПМК-4-Лекция-5-1-AVR-CortexM-STM32-ESP32]]

## Документация

- [[Рабочая программа ПМК — 4 курс|РПД-ПМК-4-курс]]
- [[ФОС ПМК — 4 курс|АккМон-ФОС-ПМК-4-курс]]

[[← ПМК|ПМК]] · [🏠 Главная](Home)
"""
    write_text(wiki_dir / "ПМК-4-курс.md", pmk4)

    rpd = section_page(
        "Рабочие программы дисциплин",
        "Рабочие программы определяют цели, компетенции, результаты обучения, "
        "объём и тематическое содержание МДК.",
        [
            ("МПС, 3 курс", "РПД-МПС-3-курс", "Рабочая программа МДК.02.01."),
            ("МПС, 4 курс", "РПД-МПС-4-курс", "Продолжение МДК.02.01 на 4 курсе."),
            ("ПМК, 3 курс", "РПД-ПМК-3-курс", "Рабочая программа МДК.02.02."),
            ("ПМК, 4 курс", "РПД-ПМК-4-курс", "Продолжение МДК.02.02 на 4 курсе."),
        ],
    )
    write_text(wiki_dir / "РПД.md", rpd)

    fos = section_page(
        "Оценочные материалы",
        "Раздел входного контроля. Основные ФОС по МПС и ПМК размещены в "
        "разделе «АккМон».",
        [
            ("3 курс", "ФОС-Входной-контроль-3-курс",
             "Определение исходного уровня знаний перед изучением МПС и ПМК."),
        ],
    )
    fos += "\n\n## Основные ФОС\n\n[[Перейти к материалам АккМон|АккМон]]\n"
    write_text(wiki_dir / "ФОС.md", fos)

    akk = section_page(
        "Аккредитационный мониторинг",
        "Банки вопросов и фонды оценочных средств по МДК.02.01 и МДК.02.02.",
        [
            ("МПС", "АккМон-Вопросы-МПС", "Вопросы к аккредитации."),
            ("ПМК", "АккМон-Вопросы-ПМК", "Вопросы к аккредитации."),
            ("МПС, 3 курс", "АккМон-ФОС-МПС-3-курс", "Фонд оценочных средств."),
            ("МПС, 4 курс", "АккМон-ФОС-МПС-4-курс", "Фонд оценочных средств."),
            ("ПМК, 3 курс", "АккМон-ФОС-ПМК-3-курс", "Фонд оценочных средств."),
            ("ПМК, 4 курс", "АккМон-ФОС-ПМК-4-курс", "Фонд оценочных средств."),
        ],
    )
    write_text(wiki_dir / "АккМон.md", akk)

    sidebar = """## 🏠 Главная
[[Главная|Home]]

---

## 🖥 МПС
[[Обзор МПС|МПС]]

**3 курс**
- [[Лекция 1. Общие понятия МПС|МПС-3-Лекция-1-Общие-понятия]]
- [[Лекция 2. Микропроцессор|МПС-3-Лекция-2-Микропроцессор]]

**4 курс**
- [[Лекция 1. Этапы проектирования|МПС-4-Лекция-1-Этапы-проектирования]]

---

## 🔧 ПМК
[[Обзор ПМК|ПМК]]

**3 курс**
- [[Лекция 1. Архитектура МК|ПМК-3-Лекция-1-Архитектура-микроконтроллеров]]
- [[Лекция 2. ARM Cortex-M|ПМК-3-Лекция-2-ARM-Cortex-M]]
- [[Лекция 3. Arduino|ПМК-3-Лекция-3-Основы-Arduino]]

**4 курс**
- [[Лекция 5.1. AVR / Cortex-M / STM32 / ESP32|ПМК-4-Лекция-5-1-AVR-CortexM-STM32-ESP32]]

---

## 📚 Документация
- [[Рабочие программы|РПД]]
- [[Оценочные материалы|ФОС]]
- [[Аккредитационный мониторинг|АккМон]]
"""
    write_text(wiki_dir / "_Sidebar.md", sidebar)

    footer = """---
**09.02.01 «Компьютерные системы и комплексы»** ·
[Основной репозиторий](https://github.com/BysonHunter/Tavrich_college) ·
Wiki формируется из материалов ветки `main`.
"""
    write_text(wiki_dir / "_Footer.md", footer)


def discover_extra_pages(source_dir: Path, page_map: dict[str, str]) -> dict[str, str]:
    roots = ["АккМон", "МПС", "ПМК", "РПД", "ФОС"]
    extras: dict[str, str] = {}
    used = set(page_map.values())

    for root_name in roots:
        root = source_dir / root_name
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            rel = p.relative_to(source_dir).as_posix()
            if p.name.lower() == "readme.md" or rel in page_map:
                continue
            page = fallback_page_name(rel)
            base = Path(page).stem
            n = 2
            while page in used:
                page = f"{base}-{n}.md"
                n += 1
            extras[rel] = page
            used.add(page)

    return extras


def clean_wiki_dir(wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    for item in wiki_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Локальная папка клона Tavrich_college")
    parser.add_argument("--wiki", required=True, help="Локальная папка клона Tavrich_college.wiki")
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--no-clean", action="store_true",
                        help="Не удалять существующие Wiki-файлы перед сборкой")
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    wiki_dir = Path(args.wiki).resolve()

    if not source_dir.exists():
        raise SystemExit(f"Исходный репозиторий не найден: {source_dir}")

    if not args.no_clean:
        clean_wiki_dir(wiki_dir)
    else:
        wiki_dir.mkdir(parents=True, exist_ok=True)

    all_map = dict(PAGE_MAP)
    extras = discover_extra_pages(source_dir, all_map)
    all_map.update(extras)

    build_navigation_pages(wiki_dir)

    copied = 0
    missing: list[str] = []

    for source_rel, target_name in sorted(all_map.items()):
        src = source_dir / Path(source_rel)
        if not src.exists():
            if source_rel in PAGE_MAP:
                missing.append(source_rel)
            continue

        content = src.read_text(encoding="utf-8")
        content = rewrite_markdown(
            content, source_rel, all_map, args.owner, args.repo, args.branch
        )

        parent = PARENT_MAP.get(source_rel)
        if parent is None:
            root = PurePosixPath(source_rel).parts[0]
            parent = {
                "МПС": "МПС",
                "ПМК": "ПМК",
                "РПД": "РПД",
                "ФОС": "ФОС",
                "АккМон": "АккМон",
            }.get(root, "Home")

        content = add_wiki_header(
            content, source_rel, parent, args.owner, args.repo, args.branch
        )

        write_text(wiki_dir / target_name, content)
        copied += 1

    if extras:
        lines = [
            "# Дополнительные материалы",
            "",
            "Эти страницы обнаружены автоматически при синхронизации и не входили "
            "в исходную фиксированную структуру Wiki.",
            "",
        ]
        for source_rel, page_file in sorted(extras.items()):
            page = Path(page_file).stem
            src = source_dir / source_rel
            title = page_title(src.read_text(encoding="utf-8"), src.stem)
            lines.append(f"- {wiki_link(title, page)} — `{source_rel}`")
        lines += ["", "[🏠 На главную](Home)"]
        write_text(wiki_dir / "Дополнительные-материалы.md", "\n".join(lines))

        sidebar_path = wiki_dir / "_Sidebar.md"
        sidebar = sidebar_path.read_text(encoding="utf-8")
        sidebar += "\n---\n\n## ➕ Дополнительно\n[[Новые материалы|Дополнительные-материалы]]\n"
        write_text(sidebar_path, sidebar)

    print(f"Wiki собрана: {wiki_dir}")
    print(f"Скопировано содержательных страниц: {copied}")
    print(f"Автоматически обнаружено дополнительных страниц: {len(extras)}")

    if missing:
        print("\nВНИМАНИЕ: ожидаемые файлы не найдены:")
        for m in missing:
            print(" -", m)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
