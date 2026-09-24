# Downloading another device's documentation

Downloader entry points live in `scripts/`. After installing the project into
`.venv`, pass the document URL as the only required argument:

```bash
.venv/bin/python scripts/fetch_cloudengine.py 'https://example.org/device/manual.pdf'
.venv/bin/python scripts/fetch_campus.py 'https://example.org/device/reference.zip'
.venv/bin/python scripts/fetch_ne40e.py 'https://example.org/device/documentation.zip'
```

Replace the example URL with the source for the desired model and release. A
direct HTTP(S) PDF, CHM or ZIP URL is supported. Huawei document pages of the form
`https://support.huawei.com/enterprise/en/doc/EDOC…` are converted to the associated
download endpoint. A page that requires login, a HedEx topic without a downloadable
package, or another HTML page cannot be treated as a manual; the script reports
that a direct public download URL is needed.

`--url URL` is equivalent to the positional URL. The default directory is
`data/manuals`; change it with `--destination DIRECTORY`. The document type is
detected from the response. The filename comes from the selected ZIP member or
HTTP filename; otherwise the EDOC ID or a stable URL digest is used. Path components
from remote filenames are discarded.

For an explicit local name:

```bash
.venv/bin/python scripts/fetch_cloudengine.py --url 'DOWNLOAD_URL' \
  -o data/manuals/cloudengine-MODEL-VERSION.pdf

.venv/bin/python scripts/fetch_campus.py --url 'DOWNLOAD_URL' \
  -o data/manuals/campus-MODEL-VERSION.pdf

.venv/bin/python scripts/fetch_ne40e.py --url 'DOWNLOAD_URL' \
  -o /tmp/ne40e-MODEL-VERSION.chm
```

The output extension selects PDF or CHM when a ZIP has both formats. Without an
explicit output, CloudEngine/Campus prefer PDF and NE40E prefers CHM, falling back
to the other format if that is the only one available. A single matching member
is selected automatically. A uniquely named complete `Command Reference.pdf` is
preferred to separate chapter PDFs. If several manuals remain, the script lists
them and requires `--member 'exact/path/in/archive.pdf'`; it does not silently
choose the first model or chapter.

The URL mode preserves the complete selected file. In particular, it does not
apply the old Campus chapter-19 exclusion to an unrelated model or release. It
also does not apply another manual's pinned checksum. Optional `--sha256` verifies
the downloaded HTTP payload; `--document-sha256` verifies the extracted document.
`--max-bytes` limits both downloads and extracted members (default: 4 GiB).

Beside the document, `NAME.source.json` records the supplied URL, download and final
URLs, selected member, timestamp and both checksums. Override its path with
`--source-map FILE`. The scripts stream downloads and one selected archive member,
check PDF validity or the CHM signature, and publish only completed files. Existing
documents and source maps are not overwritten.

## Parsing the downloaded document

Downloading and parsing remain separate operations. For PDFs:

```bash
.venv/bin/python -m cli_reference_corpus parse data/manuals/cloudengine-MODEL-VERSION.pdf \
  --parser cloudengine --workers 8 -o output/cloudengine-MODEL-VERSION

.venv/bin/python -m cli_reference_corpus parse data/manuals/campus-MODEL-VERSION.pdf \
  --parser campus-switch --workers 8 -o output/campus-MODEL-VERSION
```

An NE40E CHM must first be converted with `scripts/chm_to_pdf.py`. The reference
entry point is taken from that package's contents; it can differ between releases.
Use `--parser ne40e-rendered` for the converted PDF and `--parser ne40e` for an
original NE40E PDF. See [NE40E preparation](ne40e.md). A downloader accepting a new
model does not establish that its layout is supported by an existing parser.

The pinned reproduction modes remain available: CloudEngine with no URL, Campus
with `--output` and `--source-map` but no URL, and NE40E with `--manifest` and
`--destination`. Those modes retain their original checksums and preparation rules.
