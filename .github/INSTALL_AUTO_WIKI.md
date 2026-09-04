# Автоматическое обновление GitHub Wiki

Этот комплект включает автоматическую синхронизацию Wiki для репозитория:

`BysonHunter/Tavrich_college`

После установки вручную запускать `publish_wiki.cmd` при каждом изменении больше не нужно.

## Что добавить в основной репозиторий

Скопируйте папку `.github` из этого комплекта в корень `Tavrich_college`:

```text
Tavrich_college/
├── .github/
│   ├── scripts/
│   │   └── build_wiki.py
│   └── workflows/
│       └── update-wiki.yml
├── АккМон/
├── МПС/
├── ПМК/
├── РПД/
└── ФОС/
```

## Перед первым запуском

Wiki должна быть инициализирована один раз:

1. Откройте репозиторий `BysonHunter/Tavrich_college`.
2. `Settings -> General -> Features`.
3. Включите **Wikis**.
4. Откройте вкладку **Wiki**.
5. Создайте первую страницу `Home`.

После этого существует Git-репозиторий Wiki:

```text
BysonHunter/Tavrich_college.wiki.git
```

## Установка через Git

На Windows скопируйте папку `.github` из данного комплекта в локальный клон `Tavrich_college`, затем выполните:

```powershell
git add .github
git commit -m "ci: automatically update GitHub Wiki"
git push origin main
```

После `push` GitHub Actions сам запустит workflow `Update GitHub Wiki`.

## Когда Wiki обновляется автоматически

Workflow запускается после `push` в ветку `main`, если изменились:

```text
МПС/**
ПМК/**
РПД/**
ФОС/**
АккМон/**
.github/scripts/build_wiki.py
.github/workflows/update-wiki.yml
```

Также workflow можно запустить вручную:

**Actions -> Update GitHub Wiki -> Run workflow**

## Как работает синхронизация

```text
изменение лекции / РПД / ФОС
            |
            v
        git push main
            |
            v
       GitHub Actions
            |
            v
      build_wiki.py
            |
            v
 Tavrich_college.wiki.git
            |
            v
       обновлённая Wiki
```

## Изображения

Папки `images` в Wiki не копируются. `build_wiki.py` переписывает относительные ссылки на изображения так, чтобы Wiki загружала файлы напрямую из основного репозитория.

Поэтому замена изображения в основном репозитории под тем же именем сразу отражается в Wiki без дублирования файла.

## Новые Markdown-файлы

Генератор автоматически ищет новые `.md`-файлы внутри:

```text
МПС/
ПМК/
РПД/
ФОС/
АккМон/
```

Текущие известные лекции получают постоянные удобные имена Wiki-страниц. Новые Markdown-файлы, которых ещё нет в фиксированной карте, автоматически попадают в страницу **«Дополнительные материалы»** и в боковую навигацию.

## Авторизация

Для Wiki этого же репозитория workflow использует стандартный:

```text
GITHUB_TOKEN
```

В workflow запрошено:

```yaml
permissions:
  contents: write
```

Отдельный Personal Access Token обычно не требуется.

Если workflow получает `403`, проверьте:

**Settings -> Actions -> General -> Workflow permissions**

и убедитесь, что политика репозитория/аккаунта не запрещает запись через `GITHUB_TOKEN`.

## Где смотреть результат

На GitHub:

**Actions -> Update GitHub Wiki**

При успешном запуске последний этап `Commit and publish Wiki` завершится зелёным статусом.
