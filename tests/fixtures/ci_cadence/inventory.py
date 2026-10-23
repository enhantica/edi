"""Stable native case identities for portable cadence snapshots."""

import hashlib


def identity(node):
    path, separator, name = node.partition('::')
    if separator and path.endswith('.cpp'):
        return path + '::case_' + hashlib.sha256(name.encode()).hexdigest()
    return node


def runtime_table(source):
    lines = []
    for raw in source.splitlines(keepends=True):
        line = raw
        if raw.strip() and not raw.startswith('#'):
            seconds, node = raw.split('\t', 1)
            ending = '\n' if node.endswith('\n') else ''
            line = seconds + '\t' + identity(node.removesuffix('\n')) + ending
        lines.append(line)
    return ''.join(lines)
