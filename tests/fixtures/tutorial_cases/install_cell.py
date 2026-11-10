"""Literal published install contract and syntax-only notebook observation."""

import re

INSTALL_CELL = (
    '# Check whether easydiffraction is installed; install it if needed.\n'
    '# Required for remote environments such as Google Colab.\n'
    'import importlib.util\n'
    '\n'
    "if importlib.util.find_spec('easydiffraction') is None:\n"
    '    %pip install easydiffraction --extra-index-url '
    'https://download.easydiffraction.org/pypi/simple/\n'
)


def python_syntax(source):
    """Keep guards and line positions while replacing only IPython magic statements."""
    return re.sub(r'(?m)^([ \t]*)%pip[^\n]*', r'\1pass', source)
