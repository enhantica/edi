"""independent published table, one-table seam and licence boundary."""

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/e04_t10'


def rows(path):
    with path.open() as source:
        return list(csv.DictReader(source, delimiter='\t'))


def test_independent_fixture_has_attributable_bytes():
    provenance = json.loads((FIXTURE / 'provenance.json').read_text())
    raw = (FIXTURE / 'published-elements.tsv').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == provenance['fixture_sha256'], (
        ' I6 independent published fixture must retain its attributed bytes'
    )
    values = rows(FIXTURE / 'published-elements.tsv')
    assert len(values) == 118 and len({row['symbol'] for row in values}) == 118, (
        ' I6 independent fixture covers every published element exactly once'
    )


def test_product_table_equals_independent_published_rows():
    table = ROOT / 'data/elements/element-styles.tsv'
    assert table.is_file(), ' I6 the product owns one committed element table'
    assert rows(table) == rows(FIXTURE / 'published-elements.tsv'), (
        ' I6 every colour radius absence and row equals the independent published table'
    )
    provenance = ROOT / 'data/elements/PROVENANCE.md'
    assert provenance.is_file(), ' I6 the product table must carry its upstream provenance'
    text = provenance.read_text()
    for required in (
        'c0654956',
        'BSD-3-Clause',
        'MIT',
        'Shannon',
        'VESTA',
        hashlib.sha256(table.read_bytes()).hexdigest(),
    ):
        assert required in text, ' I6 table provenance names sources licences and exact bytes'


def test_covalent_column_equals_pinned_crysta_bond_source():
    candidates = [
        ROOT / 'build/crysta-src/data/elements/covalent-radii.tsv',
        ROOT / 'build/crysta-sdk/share/crysta/data/elements/covalent-radii.tsv',
        ROOT / 'build/crysta-prefix/share/crysta/data/elements/covalent-radii.tsv',
    ]
    source = next((path for path in candidates if path.is_file()), None)
    assert source is not None, ' I6 the pinned SDK source must expose its covalent table'
    # crysta's TSV has a provenance comment and its own two-column header.
    expected = {}
    for line in source.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        fields = line.split('\t')
        if len(fields) == 2:
            try:
                expected[fields[0]] = float(fields[1])
            except ValueError:
                continue
    assert len(expected) == 118, ' I6 engine bond table covers the full periodic table'
    product = ROOT / 'data/elements/element-styles.tsv'
    assert product.is_file(), ' I6 product table must exist for the engine parity gate'
    assert {row['symbol']: float(row['covalent']) for row in rows(product)} == expected, (
        ' I6 drawn covalent radii and independently sourced engine bond radii agree'
    )


def test_appcolors_owns_no_second_element_dictionary():
    qml = (ROOT / 'app/qml/Style/AppColors.qml').read_text()
    assert 'elementColors' not in qml, ' I20 prior app dictionary is replaced by the core table'
    assert not re.search(r'"[A-Z][a-z]?"\s*:\s*"#[0-9a-fA-F]{6}"', qml), (
        ' I20 AppColors holds no duplicate periodic colour dictionary'
    )


def test_structure_view_uses_bulk_cpp_instances():
    view = ROOT / 'app/qml/Components/StructureView.qml'
    assert view.is_file(), ' I16 the real Qt Quick 3D view replaces the placeholder'
    for path in (ROOT / 'app/qml').rglob('*.qml'):
        text = path.read_text()
        assert not re.search(r'\b(?:Repeater3D|InstanceList|RandomInstancing)\s*\{', text), (
            ' I16 all app geometry uses C++ instance buffers rather than per-entry QML'
        )
    assert not (ROOT / 'app/qml/Components/StructurePlaceholder.qml').exists(), (
        ' X1 shipped Structure page has no stale placeholder implementation'
    )


@pytest.mark.parametrize('path', ['DEPENDENCIES.md', 'app/src/app_info.cpp'])
def test_quick3d_distributed_app_licence_is_named(path):
    text = (ROOT / path).read_text()
    if path == 'app/src/app_info.cpp':
        # Before: a distribution sentence in app_info.cpp. After: the owner's
        # bundled application notice, reached by the About licence link.
        header = (ROOT / 'app/src/app_info.hpp').read_text()
        assert 'qrc:/app/DISTRIBUTION-LICENSE.md' in header, (
            'seam 20 the application licence link must reach its own bundled notice'
        )
        text = (ROOT / 'app/DISTRIBUTION-LICENSE.md').read_text()
    assert 'Qt Quick 3D' in text or 'QtQuick3D' in text, (
        ' seam 20 distributed application notice names its Quick 3D dependency'
    )
    assert 'GPL' in text, ' seam 20 Quick 3D application carries the owner-selected GPL notice'
