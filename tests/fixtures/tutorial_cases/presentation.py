"""Owner-derived presentation rules and passive observations of notebook/site output."""

import base64
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup
from defusedxml import ElementTree

from tests.fixtures.tutorial_cases.contract import ROOT

RULES = json.loads(Path(__file__).with_name('presentation.json').read_text())


def text(cell):
    source = cell.get('source', '')
    return source if isinstance(source, str) else ''.join(source)


def notebook(case, root=ROOT):
    path = root / 'docs/user/tutorials' / (case + '.ipynb')
    assert path.is_file(), 'Gate 3: every selected case has a notebook: ' + case
    return json.loads(path.read_text())


def section(record):
    tags = record['tags']
    values = {(tag['facet'], tag['label']) for tag in tags}
    if record['structure_from'] == 'hand':
        return 'Getting started'
    if ('purpose', 'Simulation') in values:
        return 'Simulation'
    if any(('fittingMode', name) in values for name in ['Joint', 'Sequential', 'Independent']):
        return 'Multiple datasets'
    return 'Single crystal' if ('sampleForm', 'sc') in values else 'Powder'


def title_parts(record):
    facets = ['sampleForm', 'probe', 'beamMode']
    code = '-'.join(
        tag['label'] for facet in facets for tag in record['tags'] if tag['facet'] == facet
    )
    assert isinstance(record.get('nav_title'), str), (
        'Gate 3/4: each case declares its short navigation title'
    )
    nav = record['nav_title']
    assert '\n' not in nav and nav.endswith(' ' + code), (
        'Gate 3/4: the navigation title is one short sample name followed by its technique code'
    )
    sample = nav[: -len(code)].strip()
    assert sample and ':' not in sample and ' on ' not in sample, (
        'Gate 3/4: navigation omits the long technique prefix and instrument phrase'
    )
    title = record['title']
    subject, separator, instrument = title.partition(' on ')
    assert separator and subject.strip() and instrument.strip() and '\n' not in title, (
        'Gate 3/4: the page title names its sample on its instrument (ADR-0080)'
    )
    assert not any(title.startswith(kind + ': ') for kind in RULES['kinds']), (
        'Gate 3/4: the section supplies the technique rather than a title prefix'
    )
    return sample, code


def chips(html):
    soup = BeautifulSoup(html, 'html.parser')
    return [
        span
        for span in soup.find_all(['span', 'img'])
        if (span.name == 'img' and span.get('src', '').startswith('data:image/svg+xml'))
        or 'background' in span.get('style', '')
        or any(word in ' '.join(span.get('class', [])) for word in ['badge', 'chip', 'tag'])
    ]


def svg_documents(node):
    result = [str(svg) for svg in node.find_all('svg')]
    for image in ([node] if node.name == 'img' else []) + node.find_all('img'):
        source = image.get('src', '')
        if source.startswith('data:image/svg+xml'):
            header, data = source.split(',', 1)
            result.append(
                base64.b64decode(data).decode() if ';base64' in header else unquote(data)
            )
    return result


def path_digest(paths):
    tokens = []
    for path in paths:
        values = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?', path)
        tokens.extend(
            token if token.isalpha() else (float(token) or 0.0).hex() for token in values
        )
    return hashlib.sha256(json.dumps(tokens, separators=(',', ':')).encode()).hexdigest()


def svg_identity(document):
    root = ElementTree.fromstring(document)
    nested = [
        item for item in root.iter() if item is not root and item.tag.split('}')[-1] == 'svg'
    ]
    assert len(nested) <= 1, 'A badge contains at most its one shared font symbol'
    symbol = nested[0] if nested else root
    paths = [item.attrib['d'] for item in symbol.iter() if item.tag.split('}')[-1] == 'path']
    assert paths == [
        item.attrib['d'] for item in root.iter() if item.tag.split('}')[-1] == 'path'
    ], 'A badge must not add an unaccounted vector symbol outside its font icon'
    assert paths, 'Gate 3/4: tag symbols embed real vector paths, without an icon-font dependency'
    assert not any(item.tag.split('}')[-1] in {'use', 'image'} for item in root.iter()), (
        'Gate 3/4: a tag icon is self-contained, never a link to another icon store'
    )
    box = symbol.attrib.get('viewBox', symbol.attrib.get('viewbox'))
    assert isinstance(box, str), 'Gate 3/4: each embedded SVG declares its view box'
    return path_digest(paths), [float(value) for value in box.split()]


def assert_tag_cell(cell, record, root=ROOT):
    assert cell['cell_type'] == 'markdown' and 'hide-in-docs' not in cell.get('metadata', {}).get(
        'tags', []
    ), 'Gate 3/4: the one tags cell is visible in Jupyter, Colab and docs'
    actual = chips(text(cell))
    assert [
        chip.get('alt') if chip.name == 'img' else chip.get_text(' ', strip=True)
        for chip in actual
    ] == [tag['label'] for tag in record['tags']], (
        'Gate 3/4: the tags cell has exactly the record tags in order; no missing or renamed label'
    )
    registry = json.loads((root / 'app/examples/tags.json').read_text())
    glyphs = json.loads(Path(__file__).with_name('glyphs.json').read_text())['glyphs']
    for chip, tag in zip(actual, record['tags'], strict=True):
        definition = registry['tags'][tag['facet']][tag['value']]
        images = svg_documents(chip)
        if chip.name == 'img':
            assert len(images) == 1
            badge = ElementTree.fromstring(images[0])
            labels = [
                ''.join(item.itertext())
                for item in badge.iter()
                if item.tag.split('}')[-1] == 'text'
            ]
            assert labels == [tag['label']] and chip['alt'] == tag['label'], (
                'The visible vector label and accessible label both retain the declared tag'
            )
            backgrounds = [item for item in badge if item.tag.split('}')[-1] == 'rect']
            assert len(backgrounds) == 1 and backgrounds[0].get('fill') not in {
                None,
                '',
                'none',
                'transparent',
            }, 'The embedded badge retains its coloured background'
        else:
            assert 'style' in chip.attrs or chip.get('class'), (
                'Gate 3/4: notebook tags are styled small coloured labels'
            )
        if definition['glyph']:
            assert len(images) == 1, 'Gate 3/4: every app glyph has one embedded SVG in its tag'
            digest, box = svg_identity(images[0])
            expected = glyphs[str(ord(definition['glyph']))]
            assert digest == expected['path_sha256'] and box == expected['viewBox'], (
                'Gate 3/4: each embedded symbol is the exact glyph from the shared app font'
            )
        else:
            assert not any(
                item.tag.split('}')[-1] in {'path', 'use', 'image'}
                for document in images
                for item in ElementTree.fromstring(document).iter()
            ), 'Gate 3/4: a tag without an app glyph must not acquire a different symbol'


def assert_overview_tag(chip, tag, root=ROOT):
    """Observe the shared icon and visible tag label as distinct accessible content."""
    registry = json.loads((root / 'app/examples/tags.json').read_text())
    definition = registry['tags'][tag['facet']][tag['value']]
    assert chip.get('data-ed-tag') == tag['facet'] and chip.get('data-ed-token') == tag['value'], (
        'An overview tag retains its exact declared facet and token'
    )
    symbols = chip.select('.ed-reference-icon')
    assert len(symbols) == bool(definition['glyph']), (
        'An overview tag has exactly its shared app icon, when declared'
    )
    for symbol in symbols:
        assert symbol.get('aria-hidden') == 'true' and symbol.get_text() == definition['glyph'], (
            'The exact shared app glyph is decorative and separate from the tag label'
        )
    label = BeautifulSoup(str(chip), 'html.parser')
    for symbol in label.select('.ed-reference-icon'):
        symbol.decompose()
    assert label.get_text(' ', strip=True) == tag['label'] == definition['label'], (
        'The overview retains the exact visible and accessible declared tag label'
    )
