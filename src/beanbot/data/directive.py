from beancount import Directive
import os


def get_source_file_path(directive: Directive) -> str | None:
    """
    Returns the path to the source file of this module.
    """
    return (
        os.path.abspath(directive.meta.get("filename", "")) if directive.meta else None
    )
