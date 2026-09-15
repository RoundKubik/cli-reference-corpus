"""Built-in profiles and explicit import-path loading for external subclasses."""
from importlib import import_module
from ..parser import BasePDFParser

BUILTINS = {
    "huawei": "cli_reference_corpus.vendors.huawei:HuaweiPDFParser",
    "cloudengine": "cli_reference_corpus.vendors.huawei:CloudEngineParser",
    "campus-switch": "cli_reference_corpus.vendors.huawei:CampusSwitchParser",
    "ne40e": "cli_reference_corpus.vendors.huawei:NE40EParser",
    "ne40e-rendered": "cli_reference_corpus.vendors.huawei:NE40ERenderedParser",
    "cisco": "cli_reference_corpus.vendors.cisco:CiscoIOSParser",
    "cisco-catalyst": "cli_reference_corpus.vendors.cisco:CiscoCatalystParser",
}


def load_parser(name: str) -> BasePDFParser:
    path = BUILTINS.get(name, name)
    module, sep, symbol = path.partition(":")
    if not sep or not symbol:
        raise ValueError(f"Unknown parser {name!r}; use {', '.join(BUILTINS)} or module:Class")
    try:
        cls = getattr(import_module(module), symbol)
    except (ImportError, AttributeError) as error:
        raise ValueError(f"Cannot load parser {path}: {error}") from error
    if not isinstance(cls, type) or not issubclass(cls, BasePDFParser):
        raise ValueError(f"{path} must be a BasePDFParser subclass")
    try:
        return cls()
    except TypeError as error:
        raise ValueError(f"Parser {path} must be concrete and accept no constructor arguments: {error}") from error
