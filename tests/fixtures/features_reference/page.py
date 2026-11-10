# SPDX-License-Identifier: BSD-3-Clause
"""Observe built feature tables and their rendered status glyphs without loading resources."""

import hashlib
import json
import re
from html.parser import HTMLParser

VOID = {
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
}
PARTS = ('crystal', 'magnetic', 'experiments')


class Element:
    def __init__(self, tag, attributes=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attributes), parent
        self.children = []

    def walk(self, tag=None):
        if tag is None or self.tag == tag:
            yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.walk(tag)

    def text(self):
        if self.tag in {'svg', 'script', 'style'}:
            return ''
        return ' '.join(
            child.text() if isinstance(child, Element) else child for child in self.children
        ).strip()

    def label(self):
        labels = [self.text()]
        for node in self.walk():
            labels.extend(
                node.attrs[key] for key in ('aria-label', 'title', 'alt') if node.attrs.get(key)
            )
        return ' '.join(labels)


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Element('root')
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def glyph(node):
    drawing = []
    for child in node.walk():
        if child.tag not in {
            'svg',
            'path',
            'rect',
            'circle',
            'ellipse',
            'polygon',
            'polyline',
            'line',
            'use',
            'g',
            'img',
        }:
            continue
        attributes = {
            key: value
            for key, value in child.attrs.items()
            if key not in {'id', 'class', 'role', 'width', 'height', 'title', 'alt'}
            and not key.startswith('aria-')
        }
        drawing.append((child.tag, attributes))
    return hashlib.sha256(json.dumps(drawing, sort_keys=True).encode()).hexdigest()


def marks(node):
    return [glyph(child) for child in node.walk() if child.tag in {'svg', 'img'}]


def interface(label):
    text = label.casefold()
    if 'command line' in text or re.search(r'\bcli\b', text):
        return 'cli'
    if 'python' in text:
        return 'python'
    if 'application' in text or re.search(r'\bapp\b', text):
        return 'application'
    return None


def part(label):
    text = label.casefold()
    if 'magnetic' in text and 'structure' in text:
        return 'magnetic'
    if 'crystal' in text and 'structure' in text:
        return 'crystal'
    if 'experiment' in text and 'structure' not in text:
        return 'experiments'
    return None


def experiment_way(text):
    if 'dataset' in text or 'data set' in text:
        return 'datasets'
    source = (
        'file'
        if 'file' in text or 'disk' in text
        else ('web' if 'web' in text or 'easydiffraction' in text else None)
    )
    prefix = 'measured_' if 'measured' in text else 'full_'
    return prefix + source if source else None


def way(label, group):
    text = label.casefold()
    rules = [
        ('project', 'project' in text),
        ('manual', 'manual' in text or 'by hand' in text),
        ('cod', bool(re.search(r'\bcod\b', text)) or 'crystallography open database' in text),
        (experiment_way(text), group == 'experiments' and experiment_way(text) is not None),
        ('collection', 'easydiffraction' in text or 'collection' in text),
        ('file', any(word in text for word in ('file', 'disk', 'cif'))),
    ]
    return next((route for route, matched in rules if matched), None)


def table_rows(table, headings):
    columns, rows = [], []
    group = next((part(title) for title in reversed(list(headings.values())) if part(title)), None)
    for row in table.walk('tr'):
        cells = [
            child
            for child in row.children
            if isinstance(child, Element) and child.tag in {'td', 'th'}
        ]
        if not cells:
            continue
        if all(cell.tag == 'th' for cell in cells) and any(
            interface(cell.label()) for cell in cells
        ):
            columns = [interface(cell.label()) for cell in cells[1:]]
            continue
        if len(cells) == 1 and part(cells[0].text()):
            group = part(cells[0].text())
            continue
        rows.append({
            'part': group,
            'label': cells[0].text(),
            'cells': cells[1:],
            'all_cells': cells,
        })
    return columns, rows


def observe(source):
    document = Document(source)
    article = next(document.root.walk('article'), None)
    assert article is not None, 'The built Features page must contain its rendered article'
    legend = {}
    for node in article.walk('li'):
        text = node.text()
        for status in ('available', 'partial', 'planned', 'proposed', 'unavailable'):
            if text.casefold().startswith(status):
                icons = marks(node)
                if icons:
                    legend[status] = {'text': text, 'mark': icons[0]}
    headings, tables = {}, []
    for node in article.walk():
        if re.fullmatch(r'h[1-6]', node.tag):
            level = int(node.tag[1])
            headings = {key: title for key, title in headings.items() if key < level}
            headings[level] = node.text()
        elif node.tag == 'table':
            titles = ' '.join(headings.values()).casefold()
            defining = bool(re.search(r'defin|creat|import', titles)) and bool(
                re.search(r'structur|experiment', titles)
            )
            columns, rows = table_rows(node, headings)
            tables.append({'definition': defining, 'columns': columns, 'rows': rows})
    return {'legend': legend, 'tables': tables}
