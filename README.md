# CLI Reference Corpus

Парсер документации Huawei CloudEngine, Huawei NE40E, Cisco Catalyst
и Huawei Campus Switch S1720/S2700/S5700/S6720.
Каждая команда сохраняется отдельно: JSON в формате NAssim и его читаемый
Markdown-рендер с тем же именем. Все подписи, заголовки и сообщения рендерера
на английском языке; исходный текст команды сохраняется. Общий Markdown всего мануала не создаётся.

## Рабочая структура

```text
data/manuals/
  huawei-cloudengine-9800-8800-6800-v300r024c00.pdf
  huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf
  huawei-ne40e-v800r024c00spc500.rendered.pdf
  cisco-catalyst9300-iosxe-17.15.x.pdf
  cisco-catalyst9500-iosxe-17.15.x.pdf
output/
  huawei-cloudengine-9800-8800-6800-v300r024c00/
  huawei-campus-s1720-s2700-s5700-s6720-v200r011c10/
  huawei-ne40e-v800r024c00spc500/
  cisco-catalyst9300-iosxe-17.15.x/
  cisco-catalyst9500-iosxe-17.15.x/
```

Название корпуса содержит производителя, модель или семейства моделей и версию ПО.
У общих справочников перечислены все семейства; корпус не фильтруется по конкретному
шасси. Соответствие моделей, версий и источников хранится в
[реестре источников](reports/sources/command-references.json).
В каждом каталоге корпуса находятся `manifest.json`, `validation.json` и
`cmd_corpus/` с отдельными парами `<раздел>_<команда>.json` и `.md`.

В `data` находятся только пять PDF. Архивы, CHM, промежуточные метаданные и
справочник Upgrade-compatible удалены. Полные корпуса и PDF хранятся локально;
`data/manuals/` и `output/` исключены из Git. `benchmarks/` и `research/`
находятся в родительском каталоге и относятся к исследованию зависимостей конфигурации.

## Источники и охват

| Корпус | Документ | Происхождение PDF |
| --- | --- | --- |
| CloudEngine 9800/8800/6800 V300R024C00 | CloudEngine 9800, 8800, and 6800 V300R024C00 Command Reference, EDOC1100439391, issue 01 (2025-01-21) | Оригинальный PDF Huawei, 12 269 страниц |
| NE40E V800R024C00SPC500 | NE40E V800R024C00SPC500 Command Reference, из пакета EDOC1100423401 | Локально сформированный полный PDF из официального CHM, 30 291 страница |
| Catalyst 9300 IOS XE 17.15.x | Command Reference, Cisco IOS XE 17.15.x (Catalyst 9300 Switches) | Оригинальный PDF Cisco, 2 642 страницы |
| Catalyst 9500 IOS XE 17.15.x | Command Reference, Cisco IOS XE 17.15.x (Catalyst 9500 Switches) | Оригинальный PDF Cisco, 2 592 страницы |
| Campus S1720/S2700/S5700/S6720 V200R011C10 | S1720, S2700, S5700, and S6720 V200R011C10 Command Reference, EDOC1000178165, issue 14 (2021-10-20) | 11 349 исходных страниц Huawei; глава 19 Upgrade-compatible исключена |

Ссылки: [CloudEngine](https://support.huawei.com/enterprise/en/doc/EDOC1100439391),
[NE40E Command Reference](https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981),
[Cisco PDF](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf).
Контрольные суммы используемых PDF и URL источников сохраняются в `manifest.json`
каждого корпуса.

**NE40E использует обычный Command Reference.** PDF включает все 14 833 темы
выбранного справочника, в том числе 14 551 описание команды. Состав независимо
сверен с оглавлением официального CHM. Номера разделов `1.N` назначены при
подготовке PDF; карта исходных тем и проверки сохранены. [Подробнее](docs/ne40e.md).
CloudEngine использует общий справочник нескольких моделей; автоматического
отбора команд по конкретному шасси нет. Для Cisco используется профиль
`cisco-catalyst`, проверенный на PDF Catalyst 9300 и 9500. [Источники Cisco](docs/cisco.md).
Campus Switch использует профиль `campus-switch`: служебные пункты Command Support
не считаются командами. В корпус входят обычные команды глав 2–18 общего справочника;
автоматического отбора по модели нет. [Источник и воспроизведение](docs/campus.md).

## Текущий результат

| Корпус | Пар JSON + Markdown | CLI-шаблонов | Команд с предупреждениями |
| --- | ---: | ---: | ---: |
| CloudEngine 9800/8800/6800 V300R024C00 | 6 672 | 15 446 | 551 |
| NE40E V800R024C00SPC500 | 14 551 | 33 151 | 379 |
| Catalyst 9300 IOS XE 17.15.x | 1 343 | 2 233 | 532 |
| Catalyst 9500 IOS XE 17.15.x | 1 321 | 2 217 | 553 |
| Campus S1720/S2700/S5700/S6720 V200R011C10 | 5 989 | 11 851 | 560 |

Все 29 876 пар проверены: Markdown соответствует JSON и метаданным, контрольные
суммы PDF совпадают с manifest. Пропусков команд относительно выбранных закладок
нет; вводные главы Cisco исключены из списка ожидаемых команд. Для NE40E
отдельно подтверждено соответствие всех команд исходному Command Reference:
[сверка источника с корпусом](reports/coverage/ne40e-source-to-corpus.json).
[Проверка всех пар и JSON Schema](reports/coverage/corpus-verification.json).

CloudEngine, NE40E и Campus Switch проходят JSON Schema для каждой записи.
У Catalyst 9300 **23 записи** не проходят строгую схему: 15 без режима и 8 без
синтаксиса. У Catalyst 9500 таких записей **19**: 11 без режима и 8 без синтаксиса.
Причины требуют проверки по конкретным страницам: отсутствие извлечённого поля
не означает, что его нет в исходном PDF. Записи сохранены с предупреждениями.
Подробности — в `validation.json` соответствующего корпуса и
[отчёте проверки](reports/coverage/README.md).

## Запуск

Python 3.10 или новее. Парсинг выполняется локально без LLM, API-ключей и сети.

```bash
cd /home/roundkubik/workdir/huawei/cli-reference-corpus
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,prepare]'
```

В текущей рабочей директории корпуса уже созданы. Следующие команды воспроизводят
их из пяти PDF; выходные каталоги должны быть новыми. Для повторного прогона
используйте другой `-o` или предварительно уберите предыдущий результат.

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-cloudengine-9800-8800-6800-v300r024c00.pdf \
  --parser cloudengine --section 2 --workers 4 -o output/huawei-cloudengine-9800-8800-6800-v300r024c00 \
  --source-url https://support.huawei.com/enterprise/en/doc/EDOC1100439391

.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --parser ne40e-rendered --workers 4 -o output/huawei-ne40e-v800r024c00spc500 \
  --source-url 'https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981'

.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/cisco-catalyst9300-iosxe-17.15.x.pdf \
  --parser cisco-catalyst --workers 4 -o output/cisco-catalyst9300-iosxe-17.15.x \
  --source-url https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf
```

Для второго корпуса Cisco:

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/cisco-catalyst9500-iosxe-17.15.x.pdf \
  --parser cisco-catalyst --workers 8 -o output/cisco-catalyst9500-iosxe-17.15.x \
  --source-url https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.pdf
```

Для Campus Switch:

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf \
  --parser campus-switch --workers 8 -o output/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10 \
  --source-url https://support.huawei.com/enterprise/en/doc/EDOC1000178165
```

`parse` автоматически создаёт обе версии каждой команды. Отдельный запуск
экспорта всего справочника в Markdown не требуется.
Для просмотра произвольного отдельного JSON остаётся команда:

```bash
.venv/bin/python -m cli_reference_corpus markdown path/to/command.json -o path/to/command.md
```

Экспорт общего Markdown корпуса сохранён в API/CLI для совместимости, но в текущем
наборе данных не используется.

## Формат команды

По умолчанию применяется схема `repository` версии 3:

- `PageTitle` — название команды;
- `CLIs` — шаблоны CLI, аргументы обозначены `<...>`;
- `FuncDef` — назначение;
- `ParentView` — режимы/представления;
- `ParaDef` — параметры, каждый с `Parameters` и `Info`;
- `Examples` — списки строк CLI с приглашением устройства;
- `UsageGuidelines` — рекомендации, предпосылки и ограничения;
- `ExtraInfo` — уровень команды, задачи и операции доступа, дополнительные разделы,
  условия применимости синтаксиса и полный исходный текст примеров с подписями и выводом.
- `related_topics` — связанные темы: название, описание/цитата, исходный раздел
  и найденные номера разделов справочника.

`--schema paper` выбирает альтернативные названия полей NAssim (`ParentViews`,
`Paras`) без `PageTitle`. В версии 3 оба варианта сохраняют `UsageGuidelines`,
`ExtraInfo` и `related_topics`.
Схемы находятся в [schemas/](schemas/). Чтение старых JSON без `UsageGuidelines`
и `related_topics` поддерживается. [Правила сбора дополнительных сведений](docs/additional-information.md). Markdown строится из сериализуемых полей JSON; название, страницы
и предупреждения добавляются из метаданных извлечения.

`manifest.json` связывает `file` и `markdown_file` каждой команды с её названием,
разделом и физическими страницами PDF (с 1). `validation.json` содержит количество
команд, шаблонов и примеров, пропуски относительно закладок и предупреждения.
В `cmd_corpus/` лежат только пары команд; отчёты находятся на уровень выше.

## Проверка полноты

Аудит всех страниц пяти PDF не обнаружил пропущенных самостоятельных описаний
команд. Однако это не гарантия полноты их содержимого: подтверждены потери
примеров в массиве `Examples` и ошибки порядка синтаксиса Cisco. Полный текст
раздела примеров теперь дополнительно сохраняется в `ExtraInfo`. У 281 записи Catalyst 9300 и 120 записей
Catalyst 9500 `Examples` пуст, хотя в PDF найден раздел примеров. Подробности, конкретные страницы и воспроизводимая
проверка: [reports/coverage/README.md](reports/coverage/README.md).

## Проверки и ограничения

```bash
.venv/bin/python -m pytest -q
```

**69 тестов проходят.** Тесты используют реальные PDF-страницы Huawei и Cisco, проверяют таблицы,
многостраничные команды, шрифтовое выделение аргументов, схемы JSON, пары JSON/MD,
предупреждения, отказ от перезаписи и одинаковый результат при `workers=1` и `2`.
Тесты преобразования CHM требуют optional-зависимость `beautifulsoup4` (`prepare`).
Проверяются также границы выбранного справочника, сверка с оглавлением CHM,
сохранение вводных тем и изображений, обнаружение потерянного текста.
Для подготовки полного PDF нужны `7z` и Chrome/Chromium; сам PDF-парсер их не использует.

Корпуса предварительные: предупреждения остаются в отчётах и Markdown команд.
Наличие записи и соответствие JSON Schema не доказывают семантическую точность
каждого поля или работоспособность команды на оборудовании. Полнота относительно
закладок относится к выбранному справочнику, а не ко всем командам платформы.
Сканированные PDF требуют предварительного OCR. CLI-иерархия, проверка на устройстве
и NetBERT Mapper не реализованы.

`--strict` сохраняет результат, но возвращает код `2` при предупреждениях,
пропусках или страницах без текста. Коды `0` и `1` означают успешный экспорт
и ошибку чтения/обработки соответственно; ошибки аргументов также имеют код `2`.

## Расширение

Общее ядро — `BasePDFParser`, профили Huawei/Cisco подключаются через `--parser`.
Внешний наследник задаётся как `module:Class`. [Инструкция](docs/extending-parsers.md).
JSON и Markdown используют общую модель `Command`.
Исходный формат корпуса: [NAssim](https://github.com/AmyWorkspace/nassim).

Карта модулей и порядок чтения кода: [docs/code-structure.md](docs/code-structure.md).
