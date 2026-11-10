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
    kind, separator, body = record['title'].partition(': ')
    assert separator and kind in RULES['kinds'] and body.startswith(sample + ' on '), (
        'Gate 3/4: the page title uses a closed Kind and the navigation sample on its instrument'
    )
    assert body.removeprefix(sample + ' on ').strip(), (
        'Gate 3/4: the page title names the instrument'
    )
    return sample, code, kind


def chips(html):
    soup = BeautifulSoup(html, 'html.parser')
    return [
        span
        for span in soup.find_all('span')
        if 'background' in span.get('style', '')
        or any(word in ' '.join(span.get('class', [])) for word in ['badge', 'chip', 'tag'])
    ]


def svg_documents(node):
    result = [str(svg) for svg in node.find_all('svg')]
    for image in node.find_all('img'):
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
    paths = [item.attrib['d'] for item in root.iter() if item.tag.split('}')[-1] == 'path']
    assert paths, 'Gate 3/4: tag symbols embed real vector paths, without an icon-font dependency'
    assert not any(item.tag.split('}')[-1] in {'use', 'image'} for item in root.iter()), (
        'Gate 3/4: a tag icon is self-contained, never a link to another icon store'
    )
    box = root.attrib.get('viewBox', root.attrib.get('viewbox'))
    assert isinstance(box, str), 'Gate 3/4: each embedded SVG declares its view box'
    return path_digest(paths), [float(value) for value in box.split()]


def assert_tag_cell(cell, record, root=ROOT):
    assert cell['cell_type'] == 'markdown' and 'hide-in-docs' not in cell.get('metadata', {}).get(
        'tags', []
    ), 'Gate 3/4: the one tags cell is visible in Jupyter, Colab and docs'
    actual = chips(text(cell))
    assert [chip.get_text(' ', strip=True) for chip in actual] == [
        tag['label'] for tag in record['tags']
    ], 'Gate 3/4: the tags cell has exactly the record tags in order; no missing or renamed label'
    registry = json.loads((root / 'app/examples/tags.json').read_text())
    glyphs = json.loads(Path(__file__).with_name('glyphs.json').read_text())['glyphs']
    for chip, tag in zip(actual, record['tags'], strict=True):
        definition = registry['tags'][tag['facet']][tag['value']]
        assert 'style' in chip.attrs or chip.get('class'), (
            'Gate 3/4: notebook tags are styled small coloured labels'
        )
        images = svg_documents(chip)
        if definition['glyph']:
            assert len(images) == 1, 'Gate 3/4: every app glyph has one embedded SVG in its tag'
            digest, box = svg_identity(images[0])
            expected = glyphs[str(ord(definition['glyph']))]
            assert digest == expected['path_sha256'] and box == expected['viewBox'], (
                'Gate 3/4: each embedded symbol is the exact glyph from the shared app font'
            )
        else:
            assert not images, (
                'Gate 3/4: a tag without an app glyph must not acquire a different symbol'
            )
