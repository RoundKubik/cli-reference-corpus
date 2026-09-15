# Huawei NE40E Command Reference

Входной файл: `data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf`.
Он содержит обычный **NE40E V800R024C00SPC500 Command Reference** из официального
[пакета документации Huawei](https://support.huawei.com/enterprise/en/doc/EDOC1100423401).
[Онлайн-версия справочника](https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981).

PDF подготовлен локально из CHM: HTML-темы напечатаны через Chrome блоками и
объединены в один документ на **30 291 страницу**. Это не оригинальный PDF Huawei.
Выбран целиком раздел Command Reference: **14 833 темы**, в том числе **14 551
описание команды** и 282 вводные/группирующие темы. Соседний Debugging Command
Reference в него не входит. Старый Diagnose заменён этим справочником.

## Проверка исходного документа

- Обход дочерних HTML-тем независимо сверен с оглавлением CHM (`.hhc`):
  14 833 уникальные темы, без пропусков и лишних тем.
- Для каждой темы сохранены SHA-256 HTML и соответствующие физические страницы PDF.
  Проверены порядок тем, заголовки разделов и текст после печати.
- Все 2 508 ссылок на изображения разрешаются в локальные файлы; подготовка HTML
  сохраняет изображения и исходные таблицы. В конечном PDF также найдено
  2 508 изображений.
- Посимвольный счётчик букв и цифр не обнаружил дефицита ни в одной теме.
  Различия счётчика слов из-за переносов проверены отдельно. Эти проверки
  обнаруживают потери текста, но не являются доказательством правильного порядка
  каждого фрагмента таблицы или визуальной проверкой каждой страницы.

Происхождение и проверки сохранены вне `data`:

- [Пакет, URL и контрольные суммы](../reports/sources/ne40e-download.json).
- [Карта HTML → PDF и результаты печати](../reports/sources/ne40e-rendering.json).
- [Проверка переносов слов и изображений](../reports/sources/ne40e-text-review.json).
- [Сверка исходных команд с корпусом](../reports/coverage/ne40e-source-to-corpus.json).
- [Независимый аудит страниц PDF](../reports/coverage/huawei-ne40e-v800r024c00spc500.json).

Каждая тема начинается с новой страницы и имеет технический номер `1.N`.
Закладки PDF указывают на описания команд; вводные темы тоже присутствуют в PDF.
Номера в корпусе относятся к подготовленному PDF, а не к пагинации онлайн-справочника.

## Генерация корпуса из PDF

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --parser ne40e-rendered --workers 8 -o output/huawei-ne40e-v800r024c00spc500 \
  --source-url 'https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981'
```

Парсер читает именно PDF. HTML и CHM используются только при подготовке и проверке
источника. Полные названия команд читаются из закладок PDF, чтобы переносы
заголовков не добавляли пробелы внутрь имён. В `output/huawei-ne40e-v800r024c00spc500/cmd_corpus/` каждая команда имеет JSON и его английский
Markdown-рендер. Общий Markdown справочника не создаётся. Предупреждения извлечения
сохраняются в `validation.json` и Markdown команд. Получено 14 551 пар и 33 151
CLI-шаблон; все записи проходят JSON Schema. У 379 команд есть предупреждения
извлечения. Страница 19 559 пустая после печати, что также отражено в отчёте;
проверки исходного текста не обнаружили потери содержимого этой темы.

## Воспроизведение PDF

Дополнительно нужны `7z`, Chrome/Chromium и зависимости `.[prepare]`.
Архив и извлечённый CHM следует хранить во временном каталоге: в `data` остаются
только конечные PDF. Существующие выходные файлы и каталоги не перезаписываются.

```bash
.venv/bin/python scripts/fetch_ne40e.py \
  --manifest reports/sources/ne40e-download.json --destination /tmp/ne40e-source

.venv/bin/python scripts/chm_to_pdf.py \
  '/tmp/ne40e-source/NE40E V800R024C00SPC500 Product Documentation.chm' \
  -o /tmp/ne40e-command-reference.rendered.pdf \
  --title 'Huawei NE40E V800R024C00SPC500 Command Reference' \
  --entry-point software/nev8r10_vrpv8r16/user/ne/dc_ne_title_cli.html \
  --renderer chrome --workers 4
```

Конвертер также сохраняет `.source.json` рядом с новым PDF. При переносе конечного
PDF в `data/manuals` карту следует сохранить в `reports/sources`.
Версия Chrome и хеши модулей подготовки записаны в карте: повторная печать может
дать другой двоичный хеш PDF. Для повторения существующего корпуса достаточно
сохранённого конечного PDF.

```bash
.venv/bin/python scripts/audit_prepared_reference.py \
  --source-map reports/sources/ne40e-rendering.json \
  --pdf data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --corpus output/huawei-ne40e-v800r024c00spc500 -o reports/coverage/ne40e-source-to-corpus.json
```

Полнота здесь относится к выбранному Command Reference этой версии NE40E.
Она не означает наличие всех команд других версий ПО, диагностических справочников
или полную семантическую точность каждого поля JSON.

## Additional information (schema v3)

`ExtraInfo` now retains Default Level, Task Name and Operations, and the complete
extracted example section with captions and output. `related_topics` captures
explicit named references from the PDF text and resolves matching outline sections.
For `esi dynamic`, these include `esi dynamic-name` and `evpn redundancy-mode`.
[Extraction rules and limitations](additional-information.md).
