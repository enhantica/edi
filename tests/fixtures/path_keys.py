"""Repository manifest keys use forward slashes on every host."""

from pathlib import PurePath


def repository_key(value):
    """Retain spelling and case while representing a logical relative path portably."""
    return value.as_posix() if isinstance(value, PurePath) else str(value).replace('\\', '/')
