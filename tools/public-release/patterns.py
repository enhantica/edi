# SPDX-License-Identifier: BSD-3-Clause
"""The patterns the public-release scrub rewrites and the scan reports.

Three classes, from the public-release content review: personal and machine paths, citations of
crysta's private design records and source tree, and development-process references (task, issue
and development-hub tags). The patterns are spelled so that this file does not match itself: a
character class splits each literal word.
"""

from __future__ import annotations

import re

# A task label: two-letter epic and task numbers, in either case, with "/T6"-style siblings. It is
# never part of a longer word or path, so a file named after a task is not one.
TAG = r'(?<![\w/.-])[CEce]\d{2}-[Tt]\d+[a-z]?(?:/[Tt]\d+[a-z]?)*(?![\w-])'
# What follows a tag and belongs to it: review rounds, findings, units, items, notes and sections.
QUAL = (
    r'(?:(?:\s+|-)(?:seq[- ]?\d+[a-z]?|A\d+|P\d+[a-z]?'
    r'|review[- ]?\d+(?:\s+F\d+(?:\s*(?:,|and)\s*F\d+)*)?|F\d+|I\d+[a-z]?|D\d+|X\d+'
    r'|R\d+(?:\.\d+)*[a-z]?|note\s+\d+|plan(?:\s+[A-Z]\d+)?|unit\s+\d+[a-z]?|items?\s+\d+[a-z]?'
    r'|class\s+[A-Z]\b|§\s?[\d.]*\d[a-z]?|r\d+|step\s+\d+'
    r'|ruling(?:\s+(?:\d+[a-z]?|`?[0-9a-f]{7,40}`?))?|decision\s+\d+[a-z]?|criterion\s+\d+'
    r'|round\s+\d+))*'
)
HUB = r'[Rr]e[l]ay'
ISSUE = rf'(?:(?:edi|crysta|{HUB})\s+)?I-\d{{4}}'
TAGS = rf'(?:{TAG})(?:\s*(?:/|,|and|\+)\s*(?:{TAG}))*{QUAL}'
PROC_TOKEN = (
    rf"(?:(?:{HUB}(?:'s)?\s+(?:task\s+|packet\s+)?)?{TAGS}|{ISSUE}(?:\s+F\d+)?|ORG-\d{{4}})"
)

# Words that mark a parenthetical or a sentence as process talk.
PROCESS = re.compile(
    rf'{TAG}|I-\d{{4}}|ORG-\d{{4}}|\b{HUB}\b|\bconductor\b|\breview[- ]\d+|\bpacket\b'
    r'|\brulings?\b|~/r[u]ns|\bseq[- ]\d+'
    r"|\bowner(?:'s)?\s+(?:ruling|decision|directive|instruction|question|rule|veto"
    r'|\d{4}-\d\d-\d\d)'
    r'|\bplan\s+[A-Z]\d+\b|\bunit\s+\d+[a-z]?\b|\brepair round\b|\bF\d+\b'
)
# crysta stays private: its design records and source tree are not cited. Its public API, its
# headers and the SDK pin are kept.
PRIVATE_ADR = (
    r"crysta(?:'s)?\s+A[D]Rs?[- ]\d{4}(?:\s*(?:/|,|and)\s*(?:ADR-)?\d{4})*"
    r'(?:\s*§\s?[\d.]*\d[a-z]?)*'
)
PRIVATE_SRC = (
    r'`?crysta/(?:src|tests|tools|knowledge|corpus|docs|python|include/crysta/detail)/'
    r"[^\s`'\"),;]*`?"
    r'|https://github\.com/enhantica/c[r]ysta(?:/[^\s)>\]]*)?'
)
PRIVATE = re.compile(rf'{PRIVATE_ADR}|{PRIVATE_SRC}')
# An edi ADR citation, kept where a tag gave the reason.
EDI_ADR = (
    r'(?:edi\s+)?ADR-\d{4}'
    r'(?:\s*§\s?[\d.]*\d[a-z]?(?:\s*(?:,|and)\s*§\s?[\d.]*\d[a-z]?)*)?'
)

HOME = r'/h[o]me/'
PERSONAL = [
    (re.compile(rf'{HOME}[A-Za-z0-9_.-]+/Development/github\.com/'), '<checkout>/'),
    (re.compile(rf'{HOME}[A-Za-z0-9_.-]+/Applications/'), '<applications>/'),
    (re.compile(rf'{HOME}[A-Za-z0-9_.-]+/'), '~/'),
    (re.compile(r'/U[s]ers/[A-Za-z0-9_.-]+/'), '~/'),
]
RUN_POINTER = re.compile(r"[ \t]*[(,;]?\s*`?~/r[u]ns/[^\s`'\"),;]*`?\)?")

# A line naming a test keeps its label (test names are kept): a pytest node or function name, or a
# doctest case, suite or subcase declaration. The scrub leaves such a line alone, and the scan's
# archive-member check allows its process reference.
TEST_NAME = re.compile(
    r'\btest_\w*[ce]\d{2}_t\d+|::test_|\b(?:TEST_CASE|TEST_SUITE|SUBCASE)\s*\(\s*"'
)
# Where a test's name may carry a process reference, each recognised in its own context, and only
# the name is masked: a runtime table's node column (`<seconds>\t<file>::<name>`, or
# `UNMEASURED:<reason>` for the seconds; a doctest case's name included), a pytest node id with its
# parameter id, and a doctest declaration's quoted name. Text beside a name on the same line is
# judged as any other text.
_NODE = r'[\w./-]+\.(?:py|cpp)::'
TEST_NAME_SPANS = (
    re.compile(rf'^(?:\d+(?:\.\d+)?|UNMEASURED:[\w-]+)\t({_NODE}[^\t\n]+)$'),
    re.compile(rf'(?<![\w./-])({_NODE}(?:[A-Za-z_]\w*::)*test_\w*(?:\[[^\]\n]*\])?)'),
    re.compile(r'\b(?:TEST_CASE|TEST_SUITE|SUBCASE)\s*\(\s*("(?:[^"\\\n]|\\.)*")'),
)


def mask_test_names(line: str) -> str:
    """``line`` with each recognised test name blanked, so only the text around it is judged."""
    for rx in TEST_NAME_SPANS:
        line = rx.sub(lambda m: m[0].replace(m[1], ' ' * len(m[1]), 1), line)
    return line


# What the scan reports as a residue: the same three classes, as plain line patterns.
RESIDUE = {
    'personal path': re.compile(rf'{HOME}[A-Za-z0-9_.-]+/|/U[s]ers/[A-Za-z0-9_.-]+/|~/r[u]ns/'),
    'private citation': PRIVATE,
    'process reference': re.compile(rf'{TAG}|\bI-\d{{4}}\b|\bORG-\d{{4}}\b|\b{HUB}\b'),
}
# Per residue class, substrings of which every match contains at least one (the scan's prefilter;
# each tuple must stay complete for its pattern above). Spelled in pieces, like the patterns.
RESIDUE_LITERALS = {
    'personal path': ('/h' + 'ome/', '/U' + 'sers/', '~/r' + 'uns/'),
    'private citation': ('crysta',),
    'process reference': ('-T', '-t', 'I-', 'ORG-', 'elay'),
}
# A class tested only near its literals, in the raw bytes: every match contains one of them, its
# required core ends a few characters after it, and it starts at most the given number of bytes
# before it (four characters of up to four bytes each, a lookbehind's included). The candidate is
# the core around the literal, at the literal or one byte before it; a digit may be any Unicode
# digit, so a digit position also admits a non-ASCII byte. The process pattern's lookbehind is slow
# over long data, so it runs on a short window at each candidate instead.
RESIDUE_WINDOWS = {
    'process reference': (16, re.compile(rb'(?:-[Tt]|I-|ORG-)[0-9\x80-\xff]|[Rr]e[l]ay')),
}
