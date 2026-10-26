"""Reached source-guard escapes cover each prohibited display spelling."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ESCAPES = [
    (
        'app/qml/PrecisionEscape.qml',
        'import QtQuick\nItem { property string witness: (1.23456).toFixed(4) }',
    ),
    ('app/src/precision_escape.cpp', "auto witness = QString::number(x, 'f', 3);"),
    ('lib/edi/precision_escape.py', "witness = f'{x:.4f}'"),
    (
        'app/qml/LabelEscape.qml',
        'import QtQuick\nItem { property string witness: qsTr("it1992") }',
    ),
    (
        'app/qml/NameEscape.qml',
        'import QtQuick\nItem { property string witness: qsTr("_cell.length_a") }',
    ),
    (
        'app/qml/DisplayNameEscape.qml',
        'import QtQuick\nItem { property string witness: qsTr("Wavelength 1") }',
    ),
]


@pytest.mark.parametrize(
    ('relative', 'source'),
    ESCAPES,
    ids=['qml-fixed', 'cpp-fixed', 'python-fixed', 'raw-token', 'raw-name', 'display-label'],
)
def test_display_source_guard_reaches_new_surface_files(tmp_path, relative, source):
    root = tmp_path / 'probe'
    for folder in ('app', 'core', 'lib', 'data', 'tools/checks'):
        shutil.copytree(
            ROOT / folder,
            root / folder,
            ignore=shutil.ignore_patterns('examples', '__pycache__', '*.pyc'),
        )
    dictionary = ROOT / 'build/crysta-src/data/dictionary'
    if dictionary.is_dir():
        shutil.copytree(dictionary, root / 'build/crysta-src/data/dictionary')
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    tool = root / 'tools/checks/display_sources.py'
    assert tool.is_file(), 'The display-source guard exists and checks every declared surface'
    result = subprocess.run(
        [sys.executable, str(tool)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        'The display-source guard refuses each planted escape and identifies its reached file'
    )
    assert relative in result.stdout + result.stderr, (
        'The display-source guard refuses each planted escape and identifies its reached file'
    )
    assert 'Traceback' not in result.stderr, (
        'A planted display escape is a named refusal rather than a checker crash'
    )


def test_surfaces_call_the_dictionary_bridge_instead_of_their_own_tables():
    bridge = ROOT / 'core/src/display.cpp'
    assert bridge.is_file(), (
        'Edi exposes one core display bridge over the public engine dictionary'
    )
    source = bridge.read_text()
    assert 'crysta::' in source, (
        'The core display bridge actually consumes the engine dictionary API'
    )
    for relative in (
        'core/src/report_model.cpp',
        'core/src/report.cpp',
        'app/src/parameter_item.cpp',
        'app/src/category_list_model.cpp',
        'app/src/parameter_table_model.cpp',
    ):
        source = (ROOT / relative).read_text()
        assert 'display.hpp' in source or 'dictionary.hpp' in source, (
            'Every numeric or category consumer reaches the dictionary through the core bridge'
        )
