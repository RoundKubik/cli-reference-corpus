"""Report source words absent from the rendered PDF for conversion review."""
from collections import Counter
import re
import unicodedata

import pymupdf
from bs4 import Comment, NavigableString

BLOCKS = {"body", "div", "p", "pre", "li", "ul", "ol", "table", "tr", "td", "th",
          "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "blockquote",
          "br", "dl", "dt", "dd", "caption"}


def source_text(node) -> str:
    """Keep inline text joined; only block boundaries introduce whitespace."""
    if isinstance(node, Comment) or getattr(node, "name", None) in {"script", "style"}:
        return ""
    if isinstance(node, NavigableString):
        return str(node)
    text = "".join(source_text(child) for child in node.children)
    return f"\n{text}\n" if node.name in BLOCKS else text


def words(text: str) -> Counter:
    normalized = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    return Counter(re.findall(r"\w+", normalized))


def text_coverage(source: str, pdf: bytes) -> dict:
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        return compare_text(source, "\n".join(page.get_text() for page in document))


def compare_text(source: str, rendered: str) -> dict:
    expected, actual = words(source), words(rendered)
    missing = expected - actual
    expected_characters = Counter("".join(word * count for word, count in expected.items()))
    actual_characters = Counter("".join(word * count for word, count in actual.items()))
    missing_characters = expected_characters - actual_characters
    return {
        "source_words": expected.total(),
        "missing_word_count": missing.total(),
        "missing_words": dict(missing),
        "missing_character_count": missing_characters.total(),
        "missing_characters": dict(missing_characters),
        "note": "Token census; line wrapping and joined spans can cause differences. Not a semantic check.",
    }
