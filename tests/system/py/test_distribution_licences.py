"""The distribution's licence list is checked against its actual bundled files."""

import os
import re
from pathlib import Path

import pytest

from tests.integration.py.test_table_and_about_contract import dependency_matrix

# Filenames identify compiled/bundled components independently of the overview table.
FILES = {
    'nanobind': ('*nanobind*',),
    'robin-map': ('*robin*map*',),
    'Qt': ('*Qt6Core*', '*Qt6Qml*', '*Qt6Quick.*'),
    'Qt Graphs': ('*Qt6Graphs*',),
    'Qt Quick 3D': ('*Qt6Quick3D*',),
    'Qt Shader Tools': ('*Qt6ShaderTools*',),
    'plotly.js': ('*plotly*.js',),
    'three.js': ('*three*.js', '*OrbitControls.js'),
}


@pytest.mark.parametrize(
    ('surface', 'variable'),
    [
        ('desktop', 'EDI_DESKTOP_BUNDLE'),
        ('web', 'EDI_WEB_BUNDLE'),
        ('python', 'EDI_PYTHON_BUNDLE'),
        ('cli', 'EDI_CLI_BUNDLE'),
    ],
)
def test_delivered_surface_lists_only_its_bundled_components(surface, variable):
    matrix = dependency_matrix()
    bundle = os.environ.get(variable)
    assert bundle and Path(bundle).is_dir(), (
        'The licence gate needs the actual unpacked distribution at ' + variable
    )
    root = Path(bundle)
    notices = [p for p in root.rglob('*') if p.is_file() and p.name == 'THIRD-PARTY-NOTICES']
    assert notices, 'Each actual distribution carries its own component notices'
    listed = '\n'.join(p.read_text(errors='replace') for p in notices)
    entries = re.findall(r'^- ([^|]+)\| licence:', listed, re.MULTILINE)
    listed_names = set()
    for entry in entries:
        names = [
            name
            for name in matrix
            if entry.strip() == name or entry.strip().startswith(name + ' ')
        ]
        assert names, 'Every bundled notice entry names a component in the overview: ' + entry
        listed_names.add(max(names, key=len))
    absent = {'', '-', '—', 'no', 'n/a'}
    for name, columns in matrix.items():
        required = columns[surface].casefold() not in absent
        assert (name in listed_names) == required, (
            'A delivered licence list contains exactly its own overview column: '
            + surface
            + '/'
            + name
        )
    for name, patterns in FILES.items():
        bundled = any(any(root.rglob(pattern)) for pattern in patterns)
        if bundled:
            assert name in matrix and matrix[name][surface].casefold() not in absent, (
                'A real bundled library needs its licence on this surface: ' + surface + '/' + name
            )
    if surface == 'desktop':
        assert not any(root.rglob('*plotly*.js')), (
            'The desktop distribution does not bundle report-only plotly.js'
        )
        assert 'diffraction-lib' not in listed_names and 'plotly.js' not in listed_names, (
            'The desktop About list excludes API references and report-only libraries'
        )
