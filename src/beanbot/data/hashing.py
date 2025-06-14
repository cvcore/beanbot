"""Hashing utilities for BeanBot data types."""

from beancount import Directive
from beancount.parser.printer import EntryPrinter
import hashlib


def stable_hash(entry: Directive) -> str:
    """Generate a stable hash for a Beancount directive.

    The hash value is assumed to be stable across runs, and will only change if
    the content of the directive changes."""

    if not hasattr(stable_hash, "printer"):
        stable_hash.printer = EntryPrinter()
    printer = stable_hash.printer

    entry_str = printer(entry)
    return hashlib.sha256(entry_str.encode("utf-8")).hexdigest()
