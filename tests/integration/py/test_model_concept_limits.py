"""The user-facing concept explains the scientific preconditions and tool limits."""

import re
from html.parser import HTMLParser
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parents[3]


class VisibleConceptText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.excluded_depth = 0

    def handle_starttag(self, tag, _attrs):
        if tag in {'script', 'style', 'pre', 'code'}:
            self.excluded_depth += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'pre', 'code'} and self.excluded_depth:
            self.excluded_depth -= 1

    def handle_data(self, data):
        if not self.excluded_depth:
            self.parts.append(data)


def visible_text(path):
    parser = VisibleConceptText()
    parser.feed(markdown.markdown(path.read_text()))
    return re.sub(r'\s+', ' ', ' '.join(parser.parts).lower())


def nav_paths(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from nav_paths(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from nav_paths(child)


def test_user_concept_navigation_explains_model_preconditions_and_search_limits():
    navigation = yaml.safe_load((ROOT / 'mkdocs.yml').read_text())['nav']
    paths = set(nav_paths(navigation))
    candidates = []
    for name in paths:
        if not (name.startswith('user/') and name.endswith('.md')):
            continue
        page = ROOT / 'docs' / name
        title = page.read_text() if page.is_file() else ''
        if (
            'concept' in name.lower()
            or 'model' in name.lower()
            or re.search(r'(?m)^# .*\b(concepts?|models?|scope|what edi)\b', title.lower())
        ):
            candidates.append(page)
    assert candidates, 'The user navigation exposes a concept page about the supplied model'
    for path in candidates:
        assert path.is_file(), (
            'Every navigated model concept resolves to an actual documentation page'
        )
    pages = [visible_text(path) for path in candidates]
    suitable = [
        page
        for page in pages
        if re.search(r'\bsymmetr\w*\b', page)
        and re.search(r'\bcomposition\b', page)
        and re.search(r'\b(correct|right|appropriate|known)\b', page)
        and re.search(r'\b(start\w*|initial)\b', page)
        and re.search(r'\b(reasonable|plausible|close|approximate|sensible)\b', page)
        and re.search(r'\b(fit\w*|optimis\w*|optimiz\w*)\b', page)
        and re.search(
            r'\b(off|imperfect|inaccurate|approximate|wrong|incorrect|not exact)\b', page
        )
    ]
    assert suitable, (
        'A navigated concept explains fitting an imperfect model with correct symmetry and '
        'composition and reasonable starting values'
    )
    negative = (
        r'(?:\bno\b|\bnot\b|\bwithout\b|doesn.t|cannot|can.t|outside|out of scope|'
        r'unsupported|lacks)'
    )
    structure = r'(?:structure.{0,12}sol(?:ution|ving)|solv\w*.{0,25}structures?)'
    propagation = (
        r'(?:propagation.{0,15}vectors?.{0,50}search|search.{0,50}propagation.{0,15}vectors?)'
    )
    assert any(
        re.search(
            negative + r'.{0,170}' + structure + '|' + structure + r'.{0,170}' + negative, page
        )
        and re.search(
            negative + r'.{0,170}' + propagation + '|' + propagation + r'.{0,170}' + negative, page
        )
        for page in suitable
    ), (
        'The same concept states that structure solution and propagation-vector search '
        'are unavailable'
    )
