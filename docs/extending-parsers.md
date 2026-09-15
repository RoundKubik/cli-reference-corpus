# Как добавить производителя или новую вёрстку

`BasePDFParser` отвечает за открытие PDF, диапазоны страниц, ограниченную очередь
процессов чтения, границы команд, накопление полей, проверку покрытия по закладкам
и модель `Command`. JSON и Markdown работают с этой моделью независимо от профиля.
Для другой вёрстки нужно описать её отличия в наследнике; менять CLI и экспортёры
не требуется.

Реализации:

- [`BasePDFParser`](../src/cli_reference_corpus/parser.py) — общий алгоритм и `CommandBuilder`.
- [`HuaweiPDFParser`](../src/cli_reference_corpus/vendors/huawei.py) — нумерация, колонтитулы,
  синтетический курсив, `undo`, приглашения Huawei. `CloudEngineParser` и `NE40EParser`
  наследуют эти правила; `NE40ERenderedParser` задаёт поля промежуточного PDF из CHM.
- [`CiscoIOSParser`](../src/cli_reference_corpus/vendors/cisco.py) — пример для ненумерованных
  команд с закладками, курсивных аргументов, `Syntax Description`, `Command Modes`,
  `Router(config)#`. Проверен на синтетическом PDF. Для реального IOS/NX-OS PDF
  потребуется сверить размеры шрифтов, расположение заголовков и таблицы.
- `CiscoCatalystParser` (`--parser cisco-catalyst`) — профиль PDF Catalyst 9300 и 9500
  IOS XE 17.15.x: боковые заголовки, таблицы с горизонтальными границами,
  переносы названий и фрагменты синтаксиса. Проверяется на исходных PDF-страницах.

## Минимальный наследник

Файл `my_parser.py` в текущем каталоге:

```python
from cli_reference_corpus.vendors.cisco import CiscoIOSParser

class MyCiscoParser(CiscoIOSParser):
    header_margin = 60
    footer_margin = 45
    section_aliases = {
        **CiscoIOSParser.section_aliases,
        "Application Notes": "Usage Guidelines",
        "Command Syntax": "Format",
    }
```

```bash
PYTHONPATH=. .venv/bin/python -m cli_reference_corpus parse manual.pdf \
  --parser my_parser:MyCiscoParser --workers 4 -o output/my-cisco
# JSON и Markdown каждой команды уже находятся в output/my-cisco/cmd_corpus/.
```

Или напрямую:

```python
from my_parser import MyCiscoParser
from cli_reference_corpus.corpus import write_corpus
from pathlib import Path

if __name__ == "__main__":  # обязателен при workers > 1 в пользовательском скрипте
    source = Path("manual.pdf")
    result = MyCiscoParser().parse(source, workers=4)
    write_corpus(result, source, Path("output/my-cisco"), "repository")
```

## Точки расширения

| Метод / атрибут | Когда переопределять |
| --- | --- |
| `header_margin`, `footer_margin`, `footer_pattern` | Колонтитулы и поля страницы |
| `read_page(page, header, footer)` | Две колонки, таблицы без рамок, особый порядок текста |
| `table_options` | Аргументы `Page.find_tables`, например стратегии поиска линий |
| `outline_entries(doc)` | Закладки не соответствуют командам или нужна другая схема идентификаторов |
| `command_heading(event, page, outline)` | Нумерованный/ненумерованный заголовок, размер, координаты |
| `section_aliases`, `field_min_size`, `field_heading(event)` | Названия и оформление разделов команды |
| `add_preamble(builder, event)` | Описание и синтаксис до первого именованного раздела |
| `keyword_span(span)` | Отличие аргументов от литералов по начертанию |
| `condition_prefixes`, `inverse_keywords` | Условные варианты и обратные команды |
| `parse_formats`, `parse_parameters`, `parse_views`, `parse_examples` | Грамматика отдельных полей |
| `paragraphs(events)` | Абзацы, списки и текстовые таблицы |
| `create_builder(heading)`, `build_command(builder)` | Структура описания существенно отличается |
| `in_section(id, selected)` | Иерархия разделов отличается от `1.2.3` |

`command_heading` возвращает `Heading(section, title, page, level)` или `None`.
Разделы главы тоже можно возвращать как границы: `build_command` пропускает записи
без Function/Format. Заголовок следующей главы завершает предыдущую команду.
Ненумерованные закладки по умолчанию получают стабильные иерархические ID;
Huawei сохраняет номера из документа. Название не используется как уникальный ключ:
одноимённые команды в разных представлениях остаются отдельными записями.

Промежуточные события — `Line(text, spans, bbox, page, block)` и
`Table(rows, bbox, page)`. Координаты и страницы исходные, физические страницы с 1.
Все поля складываются в `Command`; `usage_guidelines` сериализуется как
`UsageGuidelines`. Неуверенно распознанные данные следует отмечать в `warnings`.
Общие проверки полноты и синтаксиса из `model.validate` выполняются для каждого профиля.

`read_page` выполняется также в дочерних процессах; остальные методы — последовательно
в основном процессе. Класс должен находиться в импортируемом модуле, а экземпляр
должен поддерживать pickle. Не сохраняйте открытый `pymupdf.Document` в экземпляре.
Имена внешних классов передаются явно пользователем; JSON-корпус не загружает код профиля.

## Границы масштабирования

Память при извлечении страниц ограничена пакетами `workers * 4`; процессы используют
независимые PDF-документы. Готовые объекты команд и отчёт пока собираются в памяти,
поэтому это не полностью потоковый парсер корпуса. Для очень больших комплектов
можно обрабатывать отдельные главы через `--section` и экспортировать их отдельно.
Markdown читает записи по одной, делает два прохода для оглавления и содержимого.

Наследование не устраняет различия между PDF. Скан без текстового слоя требует OCR;
у OCR могут потеряться признаки аргументов. Для нового производителя сначала
проверьте несколько реальных страниц с длинным синтаксисом, продолжением таблицы,
одноимёнными командами и примерами, затем выполните полный разбор и изучите отчёт.

## Проверяемый пример расширения

В `tests/test_extensions.py` класс `CustomCiscoParser` добавляет одно название
раздела и фильтрацию строки в `read_page`. Тест создаёт двухстраничный PDF с
ненумерованными закладками, проверяет точные Function/CLIs/ParaDef/Views/Examples/
UsageGuidelines и Markdown, запускается с `workers=1` и `workers=2`.
Это проверка интерфейса наследования; она не подменяет испытание на реальном Cisco PDF.

Внутренняя композиция и обязанности модулей: [code-structure.md](code-structure.md).
